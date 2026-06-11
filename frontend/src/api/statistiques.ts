import { api } from './client';

export interface StatistiquesActiviteAgent {
  agent_id: number;
  nom: string;
  prenom: string;
  departement: string | null;
  fonction: string | null;
  courriers_crees: number;
  mises_en_copie: number;
  imputations_emises: number;
  reponses_creees: number;
  courriers_envoyes: number;
  notes_ajoutees: number;
  documents_ajoutes: number;
  validations_demandees: number;
  validations_accordees: number;
  courriers_a_traiter: number;
  courriers_en_retard: number;
}

export interface StatistiquesActiviteReponse {
  date_debut: string; // ISO YYYY-MM-DD
  date_fin: string;
  agents: StatistiquesActiviteAgent[];
}

export async function lireActiviteAgents(
  dateDebut?: string,
  dateFin?: string,
): Promise<StatistiquesActiviteReponse> {
  const params: Record<string, string> = {};
  if (dateDebut) params.date_debut = dateDebut;
  if (dateFin) params.date_fin = dateFin;
  const { data } = await api.get<StatistiquesActiviteReponse>(
    '/statistiques/activite-agents',
    { params },
  );
  return data;
}
