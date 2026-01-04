import { useState } from "react";
import FileRow from "../FileRow";
import { CaretDown, Folder } from "@phosphor-icons/react";
import { middleTruncate } from "@/utils/directories";

export default function FolderRow({
  item,
  selected,
  onRowClick,
  toggleSelection,
  isSelected,
  autoExpanded = false,
}) {
  const [expanded, setExpanded] = useState(autoExpanded);

  const handleExpandClick = (event) => {
    event.stopPropagation();
    setExpanded(!expanded);
  };

  return (
    <>
      <tr
        onClick={onRowClick}
        className={`text-[#252525] text-xs grid grid-cols-12 py-2 pl-3.5 pr-8 hover:bg-[#E5E5E5] cursor-pointer file-row ${selected ? "selected bg-[#E5E5E5]" : ""}`}
      >
        <div
          className={`col-span-6 flex gap-x-[4px] items-center text-[#252525]`}
        >
          <div
            className={`shrink-0 w-3 h-3 rounded border-[1px] border-solid border-[#545454] ${selected ? "text-[#252525]" : "text-[#252525]"} flex justify-center items-center cursor-pointer`}
            role="checkbox"
            aria-checked={selected}
            tabIndex={0}
            onClick={(event) => {
              event.stopPropagation();
              toggleSelection(item);
            }}
          >
            {selected && <div className="w-2 h-2 bg-[#252525] rounded-[2px]" />}
          </div>
          <div
            onClick={handleExpandClick}
            className={`transform transition-transform duration-200 ${expanded ? "rotate-360" : " rotate-270"
              }`}
          >
            <CaretDown className="text-base font-bold w-4 h-4 text-[#252525]" />
          </div>
          <Folder
            className="shrink-0 text-base font-bold w-4 h-4 mr-[3px] text-[#252525]"
            weight="fill"
          />
          <p className="whitespace-nowrap overflow-show max-w-[400px] text-[#252525]">
            {middleTruncate(item.name, 35)}
          </p>
        </div>
        <p className="col-span-2 pl-3.5" />
        <p className="col-span-2 pl-2" />
      </tr>
      {expanded && (
        <>
          {item.items.map((fileItem) => (
            <FileRow
              key={fileItem.id}
              item={fileItem}
              selected={isSelected(fileItem.id)}
              toggleSelection={toggleSelection}
            />
          ))}
        </>
      )}
    </>
  );
}
