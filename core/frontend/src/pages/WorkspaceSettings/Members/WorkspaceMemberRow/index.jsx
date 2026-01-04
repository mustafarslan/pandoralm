import { titleCase } from "text-case";

export default function WorkspaceMemberRow({ user }) {
  return (
    <>
      <tr className="bg-white hover:bg-gray-50 text-[#545454] text-sm font-medium transition-colors">
        <th scope="row" className="px-6 py-4 whitespace-nowrap text-[#252525]">
          {user.username}
        </th>
        <td className="px-6 py-4">{titleCase(user.role)}</td>
        <td className="px-6 py-4">{user.lastUpdatedAt}</td>
      </tr>
    </>
  );
}
