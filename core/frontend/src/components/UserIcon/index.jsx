import React, { memo } from "react";
import usePfp from "../../hooks/usePfp";
import UserDefaultPfp from "./user.svg";
import BrandLogo from "../BrandLogo";

const UserIcon = memo(({ role }) => {
  const { pfp } = usePfp();

  return (
    <div className="relative w-[35px] h-[35px] rounded-full flex-shrink-0 overflow-hidden">
      {role === "user" && <RenderUserPfp pfp={pfp} />}
      {role !== "user" && (
        <div className="flex items-center justify-center rounded-full border border-[#CFCFCF] overflow-hidden w-full h-full bg-os-surface/50 shadow-[0_0_10px_rgba(37,37,37,0.15)]">
          <BrandLogo mode="icon" className="w-5 h-5" />
        </div>
      )}
    </div>
  );
});

function RenderUserPfp({ pfp }) {
  if (!pfp)
    return (
      <img
        src={UserDefaultPfp}
        alt="User profile picture"
        className="rounded-full border-none"
      />
    );

  return (
    <img
      src={pfp}
      alt="User profile picture"
      className="absolute top-0 left-0 w-full h-full object-cover rounded-full border-none"
    />
  );
}

export default UserIcon;
