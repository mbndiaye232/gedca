import { Navigate, Route, Routes } from 'react-router-dom';
import { Layout } from './components/Layout';
import { RequireAuth } from './auth/RequireAuth';
import Login from './pages/Login';
import Accueil from './pages/Accueil';
import Profil from './pages/Profil';
import Agents from './pages/Agents';
import Departements from './pages/Departements';
import Structure from './pages/Structure';
import AuditLog from './pages/AuditLog';

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />

      {/* Routes connectées (n'importe quel rôle) */}
      <Route element={<RequireAuth />}>
        <Route element={<Layout />}>
          <Route path="/" element={<Navigate to="/accueil" replace />} />
          <Route path="/accueil" element={<Accueil />} />
          <Route path="/profil" element={<Profil />} />
        </Route>
      </Route>

      {/* Routes superviseur uniquement */}
      <Route element={<RequireAuth roles={['superviseur']} />}>
        <Route element={<Layout />}>
          <Route path="/agents" element={<Agents />} />
          <Route path="/departements" element={<Departements />} />
          <Route path="/structure" element={<Structure />} />
          <Route path="/audit-log" element={<AuditLog />} />
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/accueil" replace />} />
    </Routes>
  );
}
