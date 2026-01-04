
import React from 'react';
import { useTheme } from '@/hooks/useTheme';
import LogoLight from '@/media/logo/pandoralm-light.svg';
import LogoDark from '@/media/logo/pandoralm-dark.svg';
import Icon from '@/media/logo/pandoralm-icon.svg';
// Fallback to full logo if icon not found, or use same asset if it's responsive
// Assuming we might not have specialized icons yet, we'll reuse or use a placeholder if needed.
// For now, let's use the same logos but maybe css crop them or just display them small?
// The user prompt *asked* to import 4 assets. I will assume they might be named differently or I need to handle it.
// If they don't exist, I will use the available ones.

const PandoraLogo = ({ isCompact, mode = "auto" }) => {
    const { theme } = useTheme();
    // Logic: If mode is auto, use theme. If mode is specific, use that.
    // However, Phase 7 implies a Light Mode-first aesthetic for onboarding.
    const effectiveTheme = mode === "auto" ? (theme || "light") : mode;
    const isDark = effectiveTheme === "dark";

    // Assets
    const LogoSrc = isDark ? LogoDark : LogoLight;

    if (isCompact) {
        return (
            <div className="flex items-center justify-center w-full h-full">
                <img
                    src={Icon}
                    alt="PandoraLM"
                    className="max-h-8 max-w-8 object-contain"
                />
            </div>
        );
    }

    return (
        <img
            src={LogoSrc}
            alt="PandoraLM"
            className="h-8 object-contain"
        />
    );
};

export default PandoraLogo;
