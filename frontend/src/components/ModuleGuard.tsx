import React from "react";
import { useSelector } from "react-redux";
import { Result, Button } from "antd";
import type { RootState } from "../store";

interface ModuleGuardProps {
  moduleCode: string;
  children: React.ReactNode;
}

export const ModuleGuard: React.FC<ModuleGuardProps> = ({ moduleCode, children }) => {
  const user = useSelector((s: RootState) => s.auth.user);
  
  if (user?.is_platform_admin) {
    return <>{children}</>;
  }

  // Active modules list.
  const activeModules = user?.subscription?.active_modules;
  
  const isEnabled = !!activeModules && activeModules.includes(moduleCode);

  if (!isEnabled) {
    return (
      <div style={{ padding: "50px", background: "#0b0f19", minHeight: "80vh" }}>
        <Result
          status="403"
          title={<span style={{ color: "#fff" }}>Module Disabled</span>}
          subTitle={<span style={{ color: "rgba(255, 255, 255, 0.65)" }}>Your company's subscription does not include the {moduleCode.toUpperCase()} module.</span>}
          extra={
            <Button type="primary" onClick={() => window.location.href = "/settings"}>
              Contact Administrator / Upgrade Plan
            </Button>
          }
        />
      </div>
    );
  }

  return <>{children}</>;
};

export default ModuleGuard;
