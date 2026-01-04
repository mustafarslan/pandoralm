import React from 'react';
import NeuralGraph from '@/components/Onboarding/Visuals/NeuralGraph';

const OnboardingLayout = ({ children }) => {
    return (
        <div className="relative w-screen h-screen flex flex-col items-center justify-center overflow-hidden bg-[#F2F2F2]">
            {/* Background Visuals (z-0) */}
            <div className="absolute inset-0 z-0 overflow-hidden pointer-events-none">
                <NeuralGraph position="bottom-left" />
                <NeuralGraph position="top-right" />
            </div>

            {/* Main Content (z-10) */}
            <div className="relative z-10 w-full h-full flex items-center justify-center p-4">
                {children}
            </div>
        </div>
    );
};

export default OnboardingLayout;
