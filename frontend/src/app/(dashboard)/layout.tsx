import { auth } from "@clerk/nextjs/server";
import { redirect } from "next/navigation";
import { QueryProvider } from "@/components/providers/query-provider";
import { TooltipProvider } from "@/components/ui/tooltip";
import { Sidebar } from "@/components/layout/sidebar";

export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { userId } = await auth();
  if (!userId) redirect("/sign-in");

  return (
    <QueryProvider>
      <TooltipProvider>
        <div className="flex h-screen overflow-hidden">
          <Sidebar />
          <main className="flex flex-1 flex-col overflow-hidden">{children}</main>
        </div>
      </TooltipProvider>
    </QueryProvider>
  );
}
