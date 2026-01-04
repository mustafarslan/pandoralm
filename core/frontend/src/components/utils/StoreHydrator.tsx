import { useEffect, useState } from 'react';
import { useLayerStore } from '../../store/useLayerStore';

const StoreHydrator = ({ children }) => {
    const [hydrated, setHydrated] = useState(false);

    useEffect(() => {
        // Zustand persist middleware usually hydrates immediately if using localStorage,
        // but this component ensures we only render children after the first client-side effect.
        // This effectively avoids the "Text content does not match server-rendered HTML" warning
        // if we were using Next.js (though this is Vite, it helps with flickering too).

        // We can also check if the store is persisted if needed, but for now simple mount check is enough.
        setHydrated(true);
    }, []);

    if (!hydrated) {
        return null; // or a simplified loading spinner
    }

    return children;
};

export default StoreHydrator;
