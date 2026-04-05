import { ArrowLeft, Building2, ShieldCheck, Zap } from "lucide-react";
import Link from "next/link";
import { Scale } from "lucide-react";

export default function Enterprise() {
  return (
    <div className="min-h-screen bg-[#f8fafc] text-slate-900 font-sans relative selection:bg-blue-200">
      <header className="fixed top-0 w-full z-50 border-b-2 border-slate-200 bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-3">
            <div className="bg-blue-600 p-2 rounded-sm shadow-sm">
              <Scale className="w-5 h-5 text-white" />
            </div>
            <span className="text-xl font-extrabold tracking-tight text-slate-900">
              TechNiche<span className="text-blue-600">Legal</span>
            </span>
          </Link>
          <Link href="/" className="flex items-center gap-2 text-sm font-bold text-slate-600 hover:text-blue-600 transition-colors">
            <ArrowLeft className="w-4 h-4" /> Back to Search
          </Link>
        </div>
      </header>

      <main className="pt-32 pb-24 px-6 max-w-4xl mx-auto relative cursor-default">
        <div className="text-center mb-16 space-y-6">
          <div className="w-16 h-16 bg-blue-100 rounded-2xl flex items-center justify-center mx-auto mb-8 shadow-sm border border-blue-200">
            <Building2 className="w-8 h-8 text-blue-600" />
          </div>
          <h1 className="text-5xl md:text-5xl font-black tracking-tight text-slate-900">
            Enterprise-Grade <br />
            <span className="text-blue-600">IP Protection</span>
          </h1>
          <p className="text-xl text-slate-600 font-medium max-w-2xl mx-auto">
            Scale your R&D safely. Deploy TechNiche Legal AI across your entire engineering organization to prevent patent infringement before a single line of code is written.
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-6 mt-16">
          <div className="bg-white border-2 border-slate-200 p-6 shadow-sm hover:shadow-md transition-shadow hover:border-blue-300">
            <ShieldCheck className="w-8 h-8 text-blue-600 mb-4" />
            <h3 className="text-xl font-black mb-2">SOC2 Type II</h3>
            <p className="text-slate-600 text-sm font-medium">
              We never train our models on your proprietary product ideas. Your IP stays yours.
            </p>
          </div>
          
          <div className="bg-white border-2 border-slate-200 p-6 shadow-sm hover:shadow-md transition-shadow hover:border-blue-300">
            <Zap className="w-8 h-8 text-blue-600 mb-4" />
            <h3 className="text-xl font-black mb-2">API Access</h3>
            <p className="text-slate-600 text-sm font-medium">
              Integrate automated patent checks directly into your PR reviews and CI/CD pipelines.
            </p>
          </div>

          <div className="bg-white border-2 border-slate-200 p-6 shadow-sm hover:shadow-md transition-shadow hover:border-blue-300">
            <Building2 className="w-8 h-8 text-blue-600 mb-4" />
            <h3 className="text-xl font-black mb-2">SSO & Provisioning</h3>
            <p className="text-slate-600 text-sm font-medium">
              Seamlessly manage your team with SAML SSO, Role-Based Access Control, and audit logs.
            </p>
          </div>
        </div>

        <div className="mt-16 text-center bg-white p-12 border-2 border-slate-200 shadow-sm">
          <h2 className="text-3xl font-black mb-4">Ready to upgrade your R&D process?</h2>
          <p className="text-slate-600 font-medium mb-8">Contact our sales team to discuss custom deployments and volume pricing.</p>
          <Link href="/" className="inline-flex items-center gap-2 px-8 py-3.5 bg-slate-900 hover:bg-slate-800 text-white font-extrabold text-sm uppercase tracking-wider transition-all shadow-md hover:shadow-lg">
            Contact Sales
          </Link>
        </div>
      </main>
    </div>
  );
}
