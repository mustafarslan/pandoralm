export default function CTAButton({
  children,
  disabled = false,
  onClick,
  className = "",
}) {
  return (
    <button
      disabled={disabled}
      onClick={() => onClick?.()}
      className={`border-none text-xs px-4 py-1 font-semibold text-white rounded-lg bg-[#252525] hover:bg-[#545454] shadow-md h-[34px] -mr-8 whitespace-nowrap w-fit transition-colors duration-200 ${className}`}
    >
      <div className="flex items-center justify-center gap-2">{children}</div>
    </button>
  );
}
