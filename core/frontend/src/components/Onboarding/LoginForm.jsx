import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';

/**
 * LoginForm Component - Enterprise Authentication
 * 
 * Ink Wash Palette:
 * - #252525 (ink-black): Primary text, buttons
 * - #545454 (ink-gray): Secondary text
 * - #7D7D7D (ink-mid): Placeholders, borders
 * - #CFCFCF (ink-light): Backgrounds, dividers
 */

const LoginForm = ({ onLogin, onSSOLogin, onForgotPassword }) => {
    const { t } = useTranslation();
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setLoading(true);

        try {
            // Basic validation
            if (!email || !password) {
                throw new Error('Please fill in all fields');
            }
            if (password.length < 8) {
                throw new Error('Password must be at least 8 characters');
            }

            await onLogin({ email, password });
        } catch (err) {
            setError(err.message || 'Login failed. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    const handleSSOClick = (provider) => {
        if (onSSOLogin) {
            onSSOLogin(provider);
        }
    };

    return (
        <form onSubmit={handleSubmit} className="w-full space-y-5">
            {/* Email Field */}
            <div>
                <label
                    htmlFor="email"
                    className="block text-sm font-medium text-[#545454] mb-1.5"
                >
                    Email Address
                </label>
                <input
                    id="email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="you@company.com"
                    autoComplete="email"
                    className="w-full px-4 py-3 rounded-lg border border-[#CFCFCF] bg-white 
                     text-[#252525] placeholder-[#7D7D7D] 
                     focus:outline-none focus:ring-2 focus:ring-[#252525] focus:border-transparent
                     transition-all duration-200"
                />
            </div>

            {/* Password Field */}
            <div>
                <div className="flex justify-between items-center mb-1.5">
                    <label
                        htmlFor="password"
                        className="block text-sm font-medium text-[#545454]"
                    >
                        Password
                    </label>
                    <button
                        type="button"
                        onClick={onForgotPassword}
                        className="text-sm text-[#7D7D7D] hover:text-[#252525] transition-colors"
                    >
                        Forgot password?
                    </button>
                </div>
                <input
                    id="password"
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    autoComplete="current-password"
                    className="w-full px-4 py-3 rounded-lg border border-[#CFCFCF] bg-white 
                     text-[#252525] placeholder-[#7D7D7D] 
                     focus:outline-none focus:ring-2 focus:ring-[#252525] focus:border-transparent
                     transition-all duration-200"
                />
            </div>

            {/* Error Message */}
            {error && (
                <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm">
                    {error}
                </div>
            )}

            {/* Sign In Button */}
            <button
                type="submit"
                disabled={loading}
                className="w-full py-3 rounded-lg font-medium text-white bg-[#252525] 
                   hover:bg-[#333333] hover:scale-[1.01] 
                   disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100
                   transition-all duration-200 shadow-md"
            >
                {loading ? (
                    <span className="flex items-center justify-center gap-2">
                        <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                        </svg>
                        Signing in...
                    </span>
                ) : (
                    'Sign In'
                )}
            </button>

            {/* Divider */}
            <div className="flex items-center gap-4 my-6">
                <div className="flex-1 h-px bg-[#CFCFCF]" />
                <span className="text-sm text-[#7D7D7D]">or continue with</span>
                <div className="flex-1 h-px bg-[#CFCFCF]" />
            </div>

            {/* SSO Buttons */}
            <div className="space-y-3">
                <button
                    type="button"
                    onClick={() => handleSSOClick('oidc')}
                    className="w-full py-3 rounded-lg font-medium text-[#252525] bg-white
                     border border-[#CFCFCF] hover:border-[#7D7D7D] hover:bg-gray-50
                     transition-all duration-200 flex items-center justify-center gap-2"
                >
                    <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z" />
                    </svg>
                    Sign in with OIDC (SSO)
                </button>

                <button
                    type="button"
                    onClick={() => handleSSOClick('saml')}
                    className="w-full py-3 rounded-lg font-medium text-[#252525] bg-white
                     border border-[#CFCFCF] hover:border-[#7D7D7D] hover:bg-gray-50
                     transition-all duration-200 flex items-center justify-center gap-2"
                >
                    <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4zm0 10.99h7c-.53 4.12-3.28 7.79-7 8.94V12H5V6.3l7-3.11v8.8z" />
                    </svg>
                    Sign in with SAML (Enterprise)
                </button>
            </div>
        </form>
    );
};

export default LoginForm;
