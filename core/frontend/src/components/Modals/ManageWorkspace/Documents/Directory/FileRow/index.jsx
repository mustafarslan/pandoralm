import React from "react";
import {
  formatDateTimeAsMoment,
  getFileExtension,
  middleTruncate,
} from "@/utils/directories";
import { File } from "@phosphor-icons/react";

export default function FileRow({ item, selected, toggleSelection }) {
  return (
    <tr
      onClick={() => toggleSelection(item)}
      className={`text-[#252525] text-xs grid grid-cols-12 py-2 pl-3.5 pr-8 hover:bg-[#E5E5E5] cursor-pointer file-row ${selected ? "selected bg-[#E5E5E5]" : ""
        }`}
    >
      <div
        data-tooltip-id="directory-item"
        className="col-span-10 w-fit flex gap-x-[4px] items-center relative text-[#252525]"
        data-tooltip-content={JSON.stringify({
          title: item.title,
          date: formatDateTimeAsMoment(item?.published),
          extension: getFileExtension(item.url),
        })}
      >
        <div
          className={`shrink-0 w-3 h-3 rounded border-[1px] border-solid border-[#545454] ${selected ? "text-[#252525]" : "text-[#252525]"
            } flex justify-center items-center cursor-pointer`}
          role="checkbox"
          aria-checked={selected}
          tabIndex={0}
        >
          {selected && <div className="w-2 h-2 bg-[#252525] rounded-[2px]" />}
        </div>
        <File
          className="shrink-0 text-base font-bold w-4 h-4 mr-[3px] text-[#252525]"
          weight="fill"
        />
        <p className="whitespace-nowrap overflow-hidden text-ellipsis max-w-[400px] text-[#252525]">
          {middleTruncate(item.title, 55)}
        </p>
      </div>
      <div className="col-span-2 flex justify-end items-center">
        {item?.cached && (
          <div className="bg-theme-settings-input-active rounded-3xl">
            <p className="text-xs px-2 py-0.5">Cached</p>
          </div>
        )}
      </div>
    </tr>
  );
}
