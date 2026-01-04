export default function LLMItem({
  name,
  value,
  image,
  description,
  checked,
  onClick,
}) {
  return (
    <div
      onClick={() => onClick(value)}
      className={`w-full p-2 rounded-md hover:cursor-pointer transition-all duration-200 border-2 ${checked
          ? "bg-[#E5E5E5] border-[#252525]"
          : "bg-white border-[#7D7D7D]/50 hover:border-[#7D7D7D] hover:bg-gray-50"
        }`}
    >
      <input
        type="checkbox"
        value={value}
        className="peer hidden"
        checked={checked}
        readOnly={true}
        formNoValidate={true}
      />
      <div className="flex gap-x-4 items-center">
        <img
          src={image}
          alt={`${name} logo`}
          className="w-10 h-10 rounded-md"
        />
        <div className="flex flex-col">
          <div className="text-sm font-semibold text-[#252525]">{name}</div>
          <div className="mt-1 text-xs text-[#545454]">{description}</div>
        </div>
      </div>
    </div>
  );
}
