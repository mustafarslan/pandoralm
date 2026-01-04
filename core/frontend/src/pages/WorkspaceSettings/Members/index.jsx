import ModalWrapper from "@/components/ModalWrapper";
import { useModal } from "@/hooks/useModal";
import Admin from "@/models/admin";
import { useEffect, useState } from "react";
import * as Skeleton from "react-loading-skeleton";
import AddMemberModal from "./AddMemberModal";
import WorkspaceMemberRow from "./WorkspaceMemberRow";
import CTAButton from "@/components/lib/CTAButton";

export default function Members({ workspace }) {
  const [loading, setLoading] = useState(true);
  const [users, setUsers] = useState([]);
  const [workspaceUsers, setWorkspaceUsers] = useState([]);
  const [adminWorkspace, setAdminWorkspace] = useState(null);

  const { isOpen, openModal, closeModal } = useModal();
  useEffect(() => {
    async function fetchData() {
      const _users = await Admin.users();
      const workspaceUsers = await Admin.workspaceUsers(workspace.id);
      const adminWorkspaces = await Admin.workspaces();
      setAdminWorkspace(
        adminWorkspaces.find(
          (adminWorkspace) => adminWorkspace.id === workspace.id
        )
      );
      setWorkspaceUsers(workspaceUsers);
      setUsers(_users);
      setLoading(false);
    }
    fetchData();
  }, [workspace]);

  if (loading) {
    return (
      <Skeleton.default
        height="80vh"
        width="100%"
        highlightColor="var(--theme-bg-primary)"
        baseColor="var(--theme-bg-secondary)"
        count={1}
        className="w-full p-4 rounded-b-2xl rounded-tr-2xl rounded-tl-sm mt-6"
        containerClassName="flex w-full"
      />
    );
  }

  return (
    <div className="flex justify-between -mt-3">
      <div className="ink-table-container w-full max-w-[700px] border border-[#CFCFCF] rounded-lg overflow-hidden">
        <table className="w-full text-left">
          <thead className="bg-[#F2F2F2] border-b border-[#CFCFCF]">
            <tr>
              <th scope="col" className="px-6 py-3 text-xs font-bold text-[#252525] uppercase tracking-wider">Username</th>
              <th scope="col" className="px-6 py-3 text-xs font-bold text-[#252525] uppercase tracking-wider">Role</th>
              <th scope="col" className="px-6 py-3 text-xs font-bold text-[#252525] uppercase tracking-wider">Date Added</th>
              <th scope="col" className="px-6 py-3 text-xs font-bold text-[#252525] uppercase tracking-wider"> </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-[#E5E7EB]">
            {workspaceUsers.length > 0 ? (
              workspaceUsers.map((user, index) => (
                <WorkspaceMemberRow key={index} user={user} />
              ))
            ) : (
              <tr>
                <td className="text-center py-4 text-ink-muted" colSpan="4">
                  No workspace members
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <CTAButton onClick={openModal}>Manage Users</CTAButton>
      <ModalWrapper isOpen={isOpen}>
        <AddMemberModal
          closeModal={closeModal}
          users={users}
          workspace={adminWorkspace}
        />
      </ModalWrapper>
    </div>
  );
}
