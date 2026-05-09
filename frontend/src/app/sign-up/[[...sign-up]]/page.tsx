import { SignUp } from "@clerk/nextjs";

export default function SignUpPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-aria-50 to-white">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <h1 className="text-2xl font-bold text-aria-900">ARIA</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Create your account to get started
          </p>
        </div>
        <SignUp />
      </div>
    </div>
  );
}
