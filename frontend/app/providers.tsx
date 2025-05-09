"use client";

import { HeroUIProvider } from "@heroui/system";
import { useRouter } from "next/navigation";
import * as React from "react";
import { ToastProvider } from "@heroui/toast";
import { UserProvider } from "@/context/UserContext";
import { GameProvider } from "@/context/GameContext";

export function Providers({ children }: { children: React.ReactNode }) {
  const router = useRouter();

  return (
    <HeroUIProvider navigate={router.push}>
      <ToastProvider />
      <UserProvider>
        <GameProvider>{children}</GameProvider>
      </UserProvider>
    </HeroUIProvider>
  );
}
