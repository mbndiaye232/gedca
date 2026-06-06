"""Routes de gestion de l'archivage physique (6 niveaux).

CRUD sur chacun des 6 niveaux + endpoint cascade (lister les enfants d'un parent)
+ endpoint « code complet » pour assembler `SS.LL.RR.BBB.DD.SD`.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.deps import (
    AgentArchivisteOuPlus,
    AgentCourant,
    AgentSuperviseur,
    IpClient,
    SessionDB,
)
from app.models.archivage import (
    Boite,
    DossierClasseur,
    LocalSalle,
    Rayon,
    Site,
    SousDossier,
)
from app.schemas.archivage import (
    BoiteCreation,
    BoiteLecture,
    CodeComplet,
    DossierCreation,
    DossierLecture,
    EmplacementMiseAJour,
    LocalCreation,
    LocalLecture,
    NiveauResume,
    RayonCreation,
    RayonLecture,
    SiteCreation,
    SiteLecture,
    SousDossierCreation,
    SousDossierLecture,
)
from app.services.archivage import (
    code_complet_sous_dossier,
    prochain_numero,
    verifier_pas_d_enfants,
)
from app.services.audit import journaliser

router = APIRouter(prefix="/archivage", tags=["archivage"])


# ============================================================================
# Helpers communs
# ============================================================================


async def _charger_site(db, site_id: int, tenant_id: int) -> Site:
    result = await db.execute(
        select(Site).where(Site.id == site_id, Site.tenant_id == tenant_id)
    )
    site = result.scalar_one_or_none()
    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site introuvable")
    return site


async def _charger_local(db, local_id: int, tenant_id: int) -> LocalSalle:
    """Vérifie aussi que le local appartient au tenant via le site parent."""
    result = await db.execute(
        select(LocalSalle).join(Site).where(
            LocalSalle.id == local_id, Site.tenant_id == tenant_id
        )
    )
    loc = result.scalar_one_or_none()
    if loc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Local introuvable")
    return loc


async def _charger_rayon(db, rayon_id: int, tenant_id: int) -> Rayon:
    result = await db.execute(
        select(Rayon)
        .join(LocalSalle, LocalSalle.id == Rayon.local_id)
        .join(Site, Site.id == LocalSalle.site_id)
        .where(Rayon.id == rayon_id, Site.tenant_id == tenant_id)
    )
    r = result.scalar_one_or_none()
    if r is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rayon introuvable")
    return r


async def _charger_boite(db, boite_id: int, tenant_id: int) -> Boite:
    result = await db.execute(
        select(Boite)
        .join(Rayon, Rayon.id == Boite.rayon_id)
        .join(LocalSalle, LocalSalle.id == Rayon.local_id)
        .join(Site, Site.id == LocalSalle.site_id)
        .where(Boite.id == boite_id, Site.tenant_id == tenant_id)
    )
    b = result.scalar_one_or_none()
    if b is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Boîte introuvable")
    return b


async def _charger_dossier(db, dossier_id: int, tenant_id: int) -> DossierClasseur:
    result = await db.execute(
        select(DossierClasseur)
        .join(Boite, Boite.id == DossierClasseur.boite_id)
        .join(Rayon, Rayon.id == Boite.rayon_id)
        .join(LocalSalle, LocalSalle.id == Rayon.local_id)
        .join(Site, Site.id == LocalSalle.site_id)
        .where(DossierClasseur.id == dossier_id, Site.tenant_id == tenant_id)
    )
    d = result.scalar_one_or_none()
    if d is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dossier introuvable")
    return d


async def _charger_sous_dossier(db, sd_id: int, tenant_id: int) -> SousDossier:
    result = await db.execute(
        select(SousDossier)
        .join(DossierClasseur, DossierClasseur.id == SousDossier.dossier_id)
        .join(Boite, Boite.id == DossierClasseur.boite_id)
        .join(Rayon, Rayon.id == Boite.rayon_id)
        .join(LocalSalle, LocalSalle.id == Rayon.local_id)
        .join(Site, Site.id == LocalSalle.site_id)
        .where(SousDossier.id == sd_id, Site.tenant_id == tenant_id)
    )
    sd = result.scalar_one_or_none()
    if sd is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Sous-dossier introuvable"
        )
    return sd


def _payload_audit(libelle: str, **extras) -> dict:
    p = {"libelle": libelle}
    p.update({k: v for k, v in extras.items() if v is not None})
    return p


async def _maj_libelle_et_description(
    obj, body: EmplacementMiseAJour
) -> dict:
    """Applique les champs modifiables. Retourne le diff pour audit."""
    diff = {}
    if body.libelle is not None and body.libelle != obj.libelle:
        diff["libelle"] = body.libelle
        obj.libelle = body.libelle
    if body.description is not None and getattr(obj, "description", None) != body.description:
        if hasattr(obj, "description"):
            diff["description"] = body.description
            obj.description = body.description
    return diff


async def _flush_ou_409(db, type_emplacement: str) -> None:
    """Flush la session, traduit toute violation UNIQUE en HTTP 409 lisible.

    Couvre deux cas :
    - Doublon de libellé au sein du même parent (contrainte ajoutée en migration 004)
    - Doublon de numero (théoriquement impossible avec prochain_numero + FOR UPDATE,
      mais on intercepte par sécurité)
    """
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        msg = str(getattr(exc, "orig", "") or "").lower()
        if "libelle" in msg or "_libelle" in msg:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Un {type_emplacement} avec ce libellé existe déjà "
                    "à cet emplacement."
                ),
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Conflit lors de la création du {type_emplacement}.",
        ) from exc


# ============================================================================
# 1. Sites
# ============================================================================


@router.get("/sites", response_model=list[SiteLecture])
async def lister_sites(agent: AgentCourant, db: SessionDB) -> list[Site]:
    result = await db.execute(
        select(Site).where(Site.tenant_id == agent.tenant_id).order_by(Site.numero)
    )
    return list(result.scalars())


@router.post(
    "/sites",
    response_model=SiteLecture,
    status_code=status.HTTP_201_CREATED,
)
async def creer_site(
    body: SiteCreation,
    archiviste: AgentArchivisteOuPlus,
    db: SessionDB,
    request: Request,
    ip: IpClient,
) -> Site:
    numero = await prochain_numero(
        db,
        Site,
        parent_column=Site.tenant_id,
        parent_value=archiviste.tenant_id,
        cap=99,
        type_emplacement="sites",
    )
    site = Site(
        tenant_id=archiviste.tenant_id,
        numero=numero,
        libelle=body.libelle,
        description=body.description,
    )
    db.add(site)
    await _flush_ou_409(db, "site")
    await journaliser(
        db,
        tenant_id=archiviste.tenant_id,
        agent_id=archiviste.id,
        action="archivage.site.create",
        entite="sites",
        entite_id=site.id,
        payload=_payload_audit(body.libelle, numero=numero),
        ip=ip,
        user_agent=request.headers.get("user-agent"),
    )
    await db.commit()
    await db.refresh(site)
    return site


@router.put("/sites/{site_id}", response_model=SiteLecture)
async def maj_site(
    site_id: int,
    body: EmplacementMiseAJour,
    archiviste: AgentArchivisteOuPlus,
    db: SessionDB,
    request: Request,
    ip: IpClient,
) -> Site:
    site = await _charger_site(db, site_id, archiviste.tenant_id)
    diff = await _maj_libelle_et_description(site, body)
    if diff:
        await _flush_ou_409(db, "site")
        await journaliser(
            db,
            tenant_id=archiviste.tenant_id,
            agent_id=archiviste.id,
            action="archivage.site.update",
            entite="sites",
            entite_id=site.id,
            payload={"diff": diff},
            ip=ip,
            user_agent=request.headers.get("user-agent"),
        )
    await db.commit()
    await db.refresh(site)
    return site


@router.delete("/sites/{site_id}", response_model=SiteLecture)
async def supprimer_site(
    site_id: int,
    superviseur: AgentSuperviseur,
    db: SessionDB,
    request: Request,
    ip: IpClient,
) -> Site:
    site = await _charger_site(db, site_id, superviseur.tenant_id)
    await verifier_pas_d_enfants(
        db,
        enfant_table="locaux_salles",
        parent_column="site_id",
        parent_id=site.id,
        libelle_enfant="local",
    )
    await journaliser(
        db,
        tenant_id=superviseur.tenant_id,
        agent_id=superviseur.id,
        action="archivage.site.delete",
        entite="sites",
        entite_id=site.id,
        payload={"libelle": site.libelle, "numero": site.numero},
        ip=ip,
        user_agent=request.headers.get("user-agent"),
    )
    await db.delete(site)
    await db.commit()
    return site


# ============================================================================
# 2. Locaux / salles
# ============================================================================


@router.get("/sites/{site_id}/locaux", response_model=list[LocalLecture])
async def lister_locaux_du_site(
    site_id: int, agent: AgentCourant, db: SessionDB
) -> list[LocalSalle]:
    await _charger_site(db, site_id, agent.tenant_id)  # 404 si pas du tenant
    result = await db.execute(
        select(LocalSalle).where(LocalSalle.site_id == site_id).order_by(LocalSalle.numero)
    )
    return list(result.scalars())


@router.post(
    "/locaux", response_model=LocalLecture, status_code=status.HTTP_201_CREATED
)
async def creer_local(
    body: LocalCreation,
    archiviste: AgentArchivisteOuPlus,
    db: SessionDB,
    request: Request,
    ip: IpClient,
) -> LocalSalle:
    await _charger_site(db, body.site_id, archiviste.tenant_id)
    numero = await prochain_numero(
        db, LocalSalle,
        parent_column=LocalSalle.site_id,
        parent_value=body.site_id,
        cap=99,
        type_emplacement="locaux",
    )
    loc = LocalSalle(
        site_id=body.site_id, numero=numero,
        libelle=body.libelle, description=body.description,
    )
    db.add(loc)
    await _flush_ou_409(db, "local")
    await journaliser(
        db, tenant_id=archiviste.tenant_id, agent_id=archiviste.id,
        action="archivage.local.create", entite="locaux_salles", entite_id=loc.id,
        payload=_payload_audit(body.libelle, numero=numero, site_id=body.site_id),
        ip=ip, user_agent=request.headers.get("user-agent"),
    )
    await db.commit()
    await db.refresh(loc)
    return loc


@router.put("/locaux/{local_id}", response_model=LocalLecture)
async def maj_local(
    local_id: int, body: EmplacementMiseAJour,
    archiviste: AgentArchivisteOuPlus, db: SessionDB,
    request: Request, ip: IpClient,
) -> LocalSalle:
    loc = await _charger_local(db, local_id, archiviste.tenant_id)
    diff = await _maj_libelle_et_description(loc, body)
    if diff:
        await _flush_ou_409(db, "local")
        await journaliser(
            db, tenant_id=archiviste.tenant_id, agent_id=archiviste.id,
            action="archivage.local.update", entite="locaux_salles", entite_id=loc.id,
            payload={"diff": diff}, ip=ip,
            user_agent=request.headers.get("user-agent"),
        )
    await db.commit()
    await db.refresh(loc)
    return loc


@router.delete("/locaux/{local_id}", response_model=LocalLecture)
async def supprimer_local(
    local_id: int, superviseur: AgentSuperviseur, db: SessionDB,
    request: Request, ip: IpClient,
) -> LocalSalle:
    loc = await _charger_local(db, local_id, superviseur.tenant_id)
    await verifier_pas_d_enfants(
        db, enfant_table="rayons", parent_column="local_id",
        parent_id=loc.id, libelle_enfant="rayon",
    )
    await journaliser(
        db, tenant_id=superviseur.tenant_id, agent_id=superviseur.id,
        action="archivage.local.delete", entite="locaux_salles", entite_id=loc.id,
        payload={"libelle": loc.libelle}, ip=ip,
        user_agent=request.headers.get("user-agent"),
    )
    await db.delete(loc)
    await db.commit()
    return loc


# ============================================================================
# 3. Rayons
# ============================================================================


@router.get("/locaux/{local_id}/rayons", response_model=list[RayonLecture])
async def lister_rayons(
    local_id: int, agent: AgentCourant, db: SessionDB
) -> list[Rayon]:
    await _charger_local(db, local_id, agent.tenant_id)
    result = await db.execute(
        select(Rayon).where(Rayon.local_id == local_id).order_by(Rayon.numero)
    )
    return list(result.scalars())


@router.post("/rayons", response_model=RayonLecture, status_code=status.HTTP_201_CREATED)
async def creer_rayon(
    body: RayonCreation, archiviste: AgentArchivisteOuPlus, db: SessionDB,
    request: Request, ip: IpClient,
) -> Rayon:
    await _charger_local(db, body.local_id, archiviste.tenant_id)
    numero = await prochain_numero(
        db, Rayon, parent_column=Rayon.local_id, parent_value=body.local_id,
        cap=99, type_emplacement="rayons",
    )
    r = Rayon(local_id=body.local_id, numero=numero, libelle=body.libelle)
    db.add(r)
    await _flush_ou_409(db, "rayon")
    await journaliser(
        db, tenant_id=archiviste.tenant_id, agent_id=archiviste.id,
        action="archivage.rayon.create", entite="rayons", entite_id=r.id,
        payload=_payload_audit(body.libelle, numero=numero, local_id=body.local_id),
        ip=ip, user_agent=request.headers.get("user-agent"),
    )
    await db.commit()
    await db.refresh(r)
    return r


@router.put("/rayons/{rayon_id}", response_model=RayonLecture)
async def maj_rayon(
    rayon_id: int, body: EmplacementMiseAJour,
    archiviste: AgentArchivisteOuPlus, db: SessionDB,
    request: Request, ip: IpClient,
) -> Rayon:
    r = await _charger_rayon(db, rayon_id, archiviste.tenant_id)
    diff = await _maj_libelle_et_description(r, body)
    if diff:
        await _flush_ou_409(db, "rayon")
        await journaliser(
            db, tenant_id=archiviste.tenant_id, agent_id=archiviste.id,
            action="archivage.rayon.update", entite="rayons", entite_id=r.id,
            payload={"diff": diff}, ip=ip,
            user_agent=request.headers.get("user-agent"),
        )
    await db.commit()
    await db.refresh(r)
    return r


@router.delete("/rayons/{rayon_id}", response_model=RayonLecture)
async def supprimer_rayon(
    rayon_id: int, superviseur: AgentSuperviseur, db: SessionDB,
    request: Request, ip: IpClient,
) -> Rayon:
    r = await _charger_rayon(db, rayon_id, superviseur.tenant_id)
    await verifier_pas_d_enfants(
        db, enfant_table="boites", parent_column="rayon_id",
        parent_id=r.id, libelle_enfant="boîte",
    )
    await journaliser(
        db, tenant_id=superviseur.tenant_id, agent_id=superviseur.id,
        action="archivage.rayon.delete", entite="rayons", entite_id=r.id,
        payload={"libelle": r.libelle}, ip=ip,
        user_agent=request.headers.get("user-agent"),
    )
    await db.delete(r)
    await db.commit()
    return r


# ============================================================================
# 4. Boîtes (numero jusqu'à 999)
# ============================================================================


@router.get("/rayons/{rayon_id}/boites", response_model=list[BoiteLecture])
async def lister_boites(
    rayon_id: int, agent: AgentCourant, db: SessionDB
) -> list[Boite]:
    await _charger_rayon(db, rayon_id, agent.tenant_id)
    result = await db.execute(
        select(Boite).where(Boite.rayon_id == rayon_id).order_by(Boite.numero)
    )
    return list(result.scalars())


@router.post("/boites", response_model=BoiteLecture, status_code=status.HTTP_201_CREATED)
async def creer_boite(
    body: BoiteCreation, archiviste: AgentArchivisteOuPlus, db: SessionDB,
    request: Request, ip: IpClient,
) -> Boite:
    await _charger_rayon(db, body.rayon_id, archiviste.tenant_id)
    numero = await prochain_numero(
        db, Boite, parent_column=Boite.rayon_id, parent_value=body.rayon_id,
        cap=999, type_emplacement="boîtes",
    )
    b = Boite(rayon_id=body.rayon_id, numero=numero, libelle=body.libelle)
    db.add(b)
    await _flush_ou_409(db, "boîte")
    await journaliser(
        db, tenant_id=archiviste.tenant_id, agent_id=archiviste.id,
        action="archivage.boite.create", entite="boites", entite_id=b.id,
        payload=_payload_audit(body.libelle, numero=numero, rayon_id=body.rayon_id),
        ip=ip, user_agent=request.headers.get("user-agent"),
    )
    await db.commit()
    await db.refresh(b)
    return b


@router.put("/boites/{boite_id}", response_model=BoiteLecture)
async def maj_boite(
    boite_id: int, body: EmplacementMiseAJour,
    archiviste: AgentArchivisteOuPlus, db: SessionDB,
    request: Request, ip: IpClient,
) -> Boite:
    b = await _charger_boite(db, boite_id, archiviste.tenant_id)
    diff = await _maj_libelle_et_description(b, body)
    if diff:
        await _flush_ou_409(db, "boîte")
        await journaliser(
            db, tenant_id=archiviste.tenant_id, agent_id=archiviste.id,
            action="archivage.boite.update", entite="boites", entite_id=b.id,
            payload={"diff": diff}, ip=ip,
            user_agent=request.headers.get("user-agent"),
        )
    await db.commit()
    await db.refresh(b)
    return b


@router.delete("/boites/{boite_id}", response_model=BoiteLecture)
async def supprimer_boite(
    boite_id: int, superviseur: AgentSuperviseur, db: SessionDB,
    request: Request, ip: IpClient,
) -> Boite:
    b = await _charger_boite(db, boite_id, superviseur.tenant_id)
    await verifier_pas_d_enfants(
        db, enfant_table="dossiers_classeurs", parent_column="boite_id",
        parent_id=b.id, libelle_enfant="dossier",
    )
    await journaliser(
        db, tenant_id=superviseur.tenant_id, agent_id=superviseur.id,
        action="archivage.boite.delete", entite="boites", entite_id=b.id,
        payload={"libelle": b.libelle}, ip=ip,
        user_agent=request.headers.get("user-agent"),
    )
    await db.delete(b)
    await db.commit()
    return b


# ============================================================================
# 5. Dossiers classeurs
# ============================================================================


@router.get("/boites/{boite_id}/dossiers", response_model=list[DossierLecture])
async def lister_dossiers(
    boite_id: int, agent: AgentCourant, db: SessionDB
) -> list[DossierClasseur]:
    await _charger_boite(db, boite_id, agent.tenant_id)
    result = await db.execute(
        select(DossierClasseur)
        .where(DossierClasseur.boite_id == boite_id)
        .order_by(DossierClasseur.numero)
    )
    return list(result.scalars())


@router.post(
    "/dossiers", response_model=DossierLecture, status_code=status.HTTP_201_CREATED
)
async def creer_dossier(
    body: DossierCreation, archiviste: AgentArchivisteOuPlus, db: SessionDB,
    request: Request, ip: IpClient,
) -> DossierClasseur:
    await _charger_boite(db, body.boite_id, archiviste.tenant_id)
    numero = await prochain_numero(
        db, DossierClasseur, parent_column=DossierClasseur.boite_id,
        parent_value=body.boite_id, cap=99, type_emplacement="dossiers",
    )
    d = DossierClasseur(boite_id=body.boite_id, numero=numero, libelle=body.libelle)
    db.add(d)
    await _flush_ou_409(db, "dossier")
    await journaliser(
        db, tenant_id=archiviste.tenant_id, agent_id=archiviste.id,
        action="archivage.dossier.create", entite="dossiers_classeurs", entite_id=d.id,
        payload=_payload_audit(body.libelle, numero=numero, boite_id=body.boite_id),
        ip=ip, user_agent=request.headers.get("user-agent"),
    )
    await db.commit()
    await db.refresh(d)
    return d


@router.put("/dossiers/{dossier_id}", response_model=DossierLecture)
async def maj_dossier(
    dossier_id: int, body: EmplacementMiseAJour,
    archiviste: AgentArchivisteOuPlus, db: SessionDB,
    request: Request, ip: IpClient,
) -> DossierClasseur:
    d = await _charger_dossier(db, dossier_id, archiviste.tenant_id)
    diff = await _maj_libelle_et_description(d, body)
    if diff:
        await _flush_ou_409(db, "dossier")
        await journaliser(
            db, tenant_id=archiviste.tenant_id, agent_id=archiviste.id,
            action="archivage.dossier.update", entite="dossiers_classeurs",
            entite_id=d.id, payload={"diff": diff}, ip=ip,
            user_agent=request.headers.get("user-agent"),
        )
    await db.commit()
    await db.refresh(d)
    return d


@router.delete("/dossiers/{dossier_id}", response_model=DossierLecture)
async def supprimer_dossier(
    dossier_id: int, superviseur: AgentSuperviseur, db: SessionDB,
    request: Request, ip: IpClient,
) -> DossierClasseur:
    d = await _charger_dossier(db, dossier_id, superviseur.tenant_id)
    await verifier_pas_d_enfants(
        db, enfant_table="sous_dossiers", parent_column="dossier_id",
        parent_id=d.id, libelle_enfant="sous-dossier",
    )
    await journaliser(
        db, tenant_id=superviseur.tenant_id, agent_id=superviseur.id,
        action="archivage.dossier.delete", entite="dossiers_classeurs", entite_id=d.id,
        payload={"libelle": d.libelle}, ip=ip,
        user_agent=request.headers.get("user-agent"),
    )
    await db.delete(d)
    await db.commit()
    return d


# ============================================================================
# 6. Sous-dossiers + endpoint code complet
# ============================================================================


@router.get(
    "/dossiers/{dossier_id}/sous-dossiers", response_model=list[SousDossierLecture]
)
async def lister_sous_dossiers(
    dossier_id: int, agent: AgentCourant, db: SessionDB
) -> list[SousDossier]:
    await _charger_dossier(db, dossier_id, agent.tenant_id)
    result = await db.execute(
        select(SousDossier)
        .where(SousDossier.dossier_id == dossier_id)
        .order_by(SousDossier.numero)
    )
    return list(result.scalars())


@router.post(
    "/sous-dossiers", response_model=SousDossierLecture,
    status_code=status.HTTP_201_CREATED,
)
async def creer_sous_dossier(
    body: SousDossierCreation, archiviste: AgentArchivisteOuPlus, db: SessionDB,
    request: Request, ip: IpClient,
) -> SousDossier:
    await _charger_dossier(db, body.dossier_id, archiviste.tenant_id)
    numero = await prochain_numero(
        db, SousDossier, parent_column=SousDossier.dossier_id,
        parent_value=body.dossier_id, cap=99,
        type_emplacement="sous-dossiers",
    )
    sd = SousDossier(dossier_id=body.dossier_id, numero=numero, libelle=body.libelle)
    db.add(sd)
    await _flush_ou_409(db, "sous-dossier")
    await journaliser(
        db, tenant_id=archiviste.tenant_id, agent_id=archiviste.id,
        action="archivage.sous_dossier.create", entite="sous_dossiers",
        entite_id=sd.id,
        payload=_payload_audit(body.libelle, numero=numero, dossier_id=body.dossier_id),
        ip=ip, user_agent=request.headers.get("user-agent"),
    )
    await db.commit()
    await db.refresh(sd)
    return sd


@router.put("/sous-dossiers/{sd_id}", response_model=SousDossierLecture)
async def maj_sous_dossier(
    sd_id: int, body: EmplacementMiseAJour,
    archiviste: AgentArchivisteOuPlus, db: SessionDB,
    request: Request, ip: IpClient,
) -> SousDossier:
    sd = await _charger_sous_dossier(db, sd_id, archiviste.tenant_id)
    diff = await _maj_libelle_et_description(sd, body)
    if diff:
        await _flush_ou_409(db, "sous-dossier")
        await journaliser(
            db, tenant_id=archiviste.tenant_id, agent_id=archiviste.id,
            action="archivage.sous_dossier.update", entite="sous_dossiers",
            entite_id=sd.id, payload={"diff": diff}, ip=ip,
            user_agent=request.headers.get("user-agent"),
        )
    await db.commit()
    await db.refresh(sd)
    return sd


@router.delete("/sous-dossiers/{sd_id}", response_model=SousDossierLecture)
async def supprimer_sous_dossier(
    sd_id: int, superviseur: AgentSuperviseur, db: SessionDB,
    request: Request, ip: IpClient,
) -> SousDossier:
    sd = await _charger_sous_dossier(db, sd_id, superviseur.tenant_id)
    await verifier_pas_d_enfants(
        db, enfant_table="documents_sous_dossiers", parent_column="sous_dossier_id",
        parent_id=sd.id, libelle_enfant="document lié",
    )
    await journaliser(
        db, tenant_id=superviseur.tenant_id, agent_id=superviseur.id,
        action="archivage.sous_dossier.delete", entite="sous_dossiers",
        entite_id=sd.id, payload={"libelle": sd.libelle}, ip=ip,
        user_agent=request.headers.get("user-agent"),
    )
    await db.delete(sd)
    await db.commit()
    return sd


@router.get(
    "/sous-dossiers/{sd_id}/code",
    response_model=CodeComplet,
    summary="Assemble le code SS.LL.RR.BBB.DD.SD + libellés des 6 niveaux",
)
async def code_complet(
    sd_id: int, agent: AgentCourant, db: SessionDB,
) -> CodeComplet:
    row = await code_complet_sous_dossier(db, sd_id, agent.tenant_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Sous-dossier introuvable"
        )
    return CodeComplet(
        sous_dossier_id=row["sous_dossier_id"],
        code_complet=row["code_complet"],
        site=NiveauResume(numero=row["site_numero"], libelle=row["site_libelle"]),
        local=NiveauResume(numero=row["local_numero"], libelle=row["local_libelle"]),
        rayon=NiveauResume(numero=row["rayon_numero"], libelle=row["rayon_libelle"]),
        boite=NiveauResume(numero=row["boite_numero"], libelle=row["boite_libelle"]),
        dossier=NiveauResume(numero=row["dossier_numero"], libelle=row["dossier_libelle"]),
        sous_dossier=NiveauResume(
            numero=row["sous_dossier_numero"], libelle=row["sous_dossier_libelle"]
        ),
    )
