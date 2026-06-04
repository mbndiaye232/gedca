import { describe, expect, it } from 'vitest';
import { calculerStatutEcheance } from './echeance';

const today = new Date(2026, 5, 1); // 1er juin 2026

describe('calculerStatutEcheance', () => {
  it('renvoie vert si pas de date limite', () => {
    expect(calculerStatutEcheance(null, today).couleur).toBe('vert');
    expect(calculerStatutEcheance(undefined, today).joursRestants).toBeNull();
  });

  it('renvoie noir si la date est dépassée', () => {
    const hier = new Date(2026, 4, 31);
    const r = calculerStatutEcheance(hier, today);
    expect(r.couleur).toBe('noir');
    expect(r.joursRestants).toBe(-1);
  });

  it('renvoie vert si > 4 jours restants', () => {
    const dans10j = new Date(2026, 5, 11);
    const r = calculerStatutEcheance(dans10j, today);
    expect(r.couleur).toBe('vert');
    expect(r.joursRestants).toBe(10);
  });

  it.each([
    [4, 'rouge-clair'],
    [3, 'rouge'],
    [2, 'rouge'],
    [1, 'rouge-fonce'],
    [0, 'rouge-fonce'],
  ] as const)('renvoie %s pour %s jours restants', (jours, attendu) => {
    const d = new Date(today);
    d.setDate(d.getDate() + jours);
    const r = calculerStatutEcheance(d, today);
    expect(r.couleur).toBe(attendu);
    expect(r.joursRestants).toBe(jours);
  });
});
