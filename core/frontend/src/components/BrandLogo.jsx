import React from 'react';

const BrandLogo = ({ mode = 'full', className = '' }) => {
    // Mode: 'icon' -> Just the Graph Triad Symbol
    // Mode: 'full' -> Symbol + Wordmark in a Flex container

    if (mode === 'icon') {
        return (
            <img
                src="/brand/logo-symbol.svg"
                alt="PandoraLM Icon"
                className={`object-contain ${className}`}
            />
        );
    }

    return (
        <div className={`flex items-center gap-3 ${className}`}>
            <img
                src="/brand/logo-symbol.svg"
                alt="PandoraLM Symbol"
                className="h-full w-auto object-contain"
            />
            <img
                src="/brand/logo-wordmark.svg"
                alt="PandoraLM"
                className="h-[75%] w-auto object-contain"
            />
        </div>
    );
};

export default BrandLogo;
