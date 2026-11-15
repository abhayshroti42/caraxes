import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { api, getOrgId, getRole, setOrgId, setRole } from "./lib/api";

const Ctx = createContext(null);
export const useApp = () => useContext(Ctx);

export function AppProvider({ children }) {
  const { pathname } = useLocation();
  const isPublicRoute = pathname.startsWith("/gallery") || pathname.startsWith("/s/");

  const [orgs, setOrgs] = useState([]);
  const [orgId, setOrg] = useState(getOrgId());
  const [role, setRoleState] = useState(getRole());
  const [error, setError] = useState("");

  const loadOrgs = useCallback(async () => {
    try {
      setOrgs(await api("/organisations"));
    } catch (e) {
      setError(e.message);
    }
  }, []);

  useEffect(() => {
    if (!isPublicRoute) loadOrgs();
  }, [isPublicRoute, loadOrgs]);

  const chooseOrg = (id) => {
    setOrgId(id);
    setOrg(id);
  };
  const chooseRole = (r) => {
    setRole(r);
    setRoleState(r);
  };
  const createOrg = async (name) => {
    const org = await api("/organisations", { method: "POST", body: JSON.stringify({ name }) });
    await loadOrgs();
    chooseOrg(org.id);
  };

  return (
    <Ctx.Provider value={{ orgs, orgId, role, error, chooseOrg, chooseRole, createOrg }}>
      {children}
    </Ctx.Provider>
  );
}