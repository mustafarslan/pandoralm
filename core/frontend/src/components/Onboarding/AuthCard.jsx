import React, { useContext, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { AuthContext } from '@/AuthContext';
import LoginForm from './LoginForm';
import paths from '@/utils/paths';
import System from '@/models/system';
import Workspace from '@/models/workspace';

/**
 * AuthCard Component - Unified Onboarding Entry Point
 * 
 * 3-State Flow:
 * 1. Unauthenticated → Show LoginForm
 * 2. Authenticated, No Workspaces → Show WelcomeCard
 * 3. Authenticated, Has Workspaces → Redirect to Homepage
 * 
 * Ink Wash Palette:
 * - #252525 (ink-black): Primary text, buttons
 * - #545454 (ink-gray): Secondary text
 * - #7D7D7D (ink-mid): Placeholders
 * - #CFCFCF (ink-light): Dividers
 */

const AuthCard = () => {
    const navigate = useNavigate();
    const { t } = useTranslation();
    const { store, actions } = useContext(AuthContext);
    const [loading, setLoading] = useState(true);
    const [workspaces, setWorkspaces] = useState([]);
    const [showForgotPassword, setShowForgotPassword] = useState(false);

    // Check auth state and workspaces on mount
    useEffect(() => {
        async function checkAuthState() {
            setLoading(true);

            if (store.authToken) {
                // User is authenticated, check for workspaces
                try {
                    const { workspaces: userWorkspaces } = await Workspace.all();
                    setWorkspaces(userWorkspaces || []);

                    // If user has workspaces, redirect to home
                    if (userWorkspaces && userWorkspaces.length > 0) {
                        navigate(paths.home());
                        return;
                    }
                } catch (err) {
                    console.error('Failed to fetch workspaces:', err);
                }
            }

            setLoading(false);
        }

        checkAuthState();
    }, [store.authToken, navigate]);

    // Handle email/password login
    const handleLogin = async ({ email, password }) => {
        const { valid, user, token, message } = await System.requestToken({
            username: email,
            password: password,
        });

        if (!valid) {
            throw new Error(message || 'Invalid credentials');
        }

        // Store auth data immediately
        actions.updateUser(user, token);

        // Smart Redirect: Check for existing workspaces immediately
        try {
            // We use the raw fetch here to ensure we use the fresh token
            // bypassing any potential race conditions with localStorage/baseHeaders
            const headers = { 'Authorization': `Bearer ${token}` };
            // Need to import API_BASE or use window.location logic.
            // Workspace.all() might be safer if we assume localStorage is set.
            // Let's rely on Workspace.all() since localStorage is synchronous.
            const userWorkspaces = await Workspace.all();
            if (userWorkspaces && userWorkspaces.length > 0) {
                window.location.href = paths.home(); // Force a hard navigation to be safe
                return;
            }
        } catch (e) {
            console.error("Smart Redirect Check Failed:", e);
        }
    };

    // Handle SSO login redirect
    const handleSSOLogin = (provider) => {
        // Redirect to Cortex backend SSO endpoint
        // In production, this should be configured via environment variable
        const cortexBase = import.meta.env.VITE_CORTEX_API_URL || 'http://localhost:8000';
        const ssoUrl = `${cortexBase}/api/v1/auth/sso/${provider}`;
        window.location.href = ssoUrl;
    };

    // Handle forgot password
    const handleForgotPassword = () => {
        setShowForgotPassword(true);
        // Could also navigate to: navigate(paths.forgotPassword());
    };

    // Handle "Get Started" click
    const handleGetStarted = () => {
        navigate(paths.onboarding.llmPreference());
    };

    // Loading state
    if (loading) {
        return (
            <div className="relative z-10 flex justify-center items-center">
                <div className="bg-white border border-gray-100 rounded-2xl p-12 flex flex-col items-center justify-center max-w-lg w-full text-center shadow-sm">
                    <div className="animate-pulse flex flex-col items-center gap-4">
                        <div className="w-16 h-16 bg-[#CFCFCF] rounded-full" />
                        <div className="h-4 w-32 bg-[#CFCFCF] rounded" />
                    </div>
                </div>
            </div>
        );
    }

    // Forgot Password Modal (simple inline for now)
    if (showForgotPassword) {
        return (
            <div className="relative z-10 flex justify-center items-center">
                <div className="bg-white border border-gray-100 rounded-2xl p-12 flex flex-col items-center justify-center max-w-lg w-full text-center shadow-sm">
                    <h2 className="text-[#252525] text-2xl font-bold mb-4">Reset Password</h2>
                    <p className="text-[#545454] mb-6">
                        Enter your email address and we'll send you a link to reset your password.
                    </p>
                    <input
                        type="email"
                        placeholder="you@company.com"
                        className="w-full px-4 py-3 rounded-lg border border-[#CFCFCF] bg-white 
                       text-[#252525] placeholder-[#7D7D7D] mb-4
                       focus:outline-none focus:ring-2 focus:ring-[#252525]"
                    />
                    <button
                        className="w-full py-3 rounded-lg font-medium text-white bg-[#252525] 
                       hover:bg-[#333333] transition-all duration-200 mb-4"
                    >
                        Send Reset Link
                    </button>
                    <button
                        onClick={() => setShowForgotPassword(false)}
                        className="text-[#7D7D7D] hover:text-[#252525] transition-colors"
                    >
                        ← Back to login
                    </button>
                </div>
            </div>
        );
    }

    // STATE 1: Unauthenticated → Show Login Form
    if (!store.authToken) {
        return (
            <div className="relative z-10 flex justify-center items-center">
                <div className="bg-white border border-gray-100 rounded-2xl p-10 flex flex-col items-center justify-center max-w-md w-full shadow-sm">
                    {/* Header */}
                    <p className="text-[#545454] text-sm font-semibold uppercase tracking-widest mb-1">
                        {t("onboarding.home.title")}
                    </p>
                    <h1 className="text-[#252525] text-4xl font-extrabold tracking-tight mb-8 mt-2">
                        PandoraLM
                    </h1>

                    {/* Login Form */}
                    <LoginForm
                        onLogin={handleLogin}
                        onSSOLogin={handleSSOLogin}
                        onForgotPassword={handleForgotPassword}
                    />
                </div>
            </div>
        );
    }

    // STATE 2: Authenticated, No Workspaces → Show Welcome Card
    return (
        <div className="relative z-10 flex justify-center items-center">
            <div className="bg-white border border-gray-100 rounded-2xl p-12 flex flex-col items-center justify-center max-w-lg w-full text-center shadow-sm">
                <p className="text-[#545454] text-sm font-semibold uppercase tracking-widest mb-1">
                    {t("onboarding.home.title")}
                </p>
                <h1 className="text-[#252525] text-5xl font-extrabold tracking-tight mb-4 mt-2">
                    PandoraLM
                </h1>
                <p className="text-[#7D7D7D] mb-8">
                    Welcome back, <span className="font-medium text-[#545454]">{store.user?.username || 'User'}</span>.
                    Let's set up your first workspace.
                </p>
                <button
                    onClick={handleGetStarted}
                    className="w-full md:w-auto md:px-8 py-3 rounded-md font-medium text-white bg-[#252525] 
                     hover:bg-[#333333] hover:scale-[1.02] transition-all duration-200 shadow-lg"
                >
                    {t("onboarding.home.getStarted")}
                </button>
            </div>
        </div>
    );
};

export default AuthCard;
