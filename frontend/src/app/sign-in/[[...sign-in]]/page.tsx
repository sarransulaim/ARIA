import { SignIn } from "@clerk/nextjs";

export default function SignInPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-aria-50 to-white">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <h1 className="text-2xl font-bold text-aria-900">ARIA</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Analytical Research &amp; Intelligence Assistant
          </p>
        </div>
        <SignIn />
      </div>
    </div>
  );
}
