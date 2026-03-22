import { ArrowLeft, Briefcase, CheckCircle2 } from "lucide-react";
import Link from "next/link";
import { Scale } from "lucide-react";

export default function Solutions() {
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
            <Briefcase className="w-8 h-8 text-blue-600" />
          </div>
          <h1 className="text-5xl md:text-5xl font-black tracking-tight text-slate-900">
            Tailored Solutions for<br />
            <span className="text-blue-600">Every Innovator</span>
          </h1>
          <p className="text-xl text-slate-600 font-medium max-w-2xl mx-auto">
            Whether you're a solopreneur or a scaled engineering team, TechNiche Legal AI provides the tools you need to protect your intellectual property.
          </p>
        </div>

        <div className="grid md:grid-cols-2 gap-8 mt-16">
          <div className="bg-white border-2 border-slate-200 p-8 shadow-sm hover:shadow-md transition-shadow hover:border-blue-300">
            <h3 className="text-2xl font-black mb-4">For Startups</h3>
            <p className="text-slate-600 mb-6 font-medium leading-relaxed">
              Move fast and break things—except patents. Quickly vet your MVPs before you invest heavily in development.
            </p>
            <ul className="space-y-3 font-semibold text-slate-700">
              <li className="flex items-center gap-2"><CheckCircle2 className="w-5 h-5 text-blue-600" /> Early-stage idea validation</li>
              <li className="flex items-center gap-2"><CheckCircle2 className="w-5 h-5 text-blue-600" /> Competitor landscape insights</li>
              <li className="flex items-center gap-2"><CheckCircle2 className="w-5 h-5 text-blue-600" /> Fast, simple reporting</li>
            </ul>
          </div>

          <div className="bg-white border-2 border-slate-200 p-8 shadow-sm hover:shadow-md transition-shadow hover:border-blue-300">
            <h3 className="text-2xl font-black mb-4">For Legal Teams</h3>
            <p className="text-slate-600 mb-6 font-medium leading-relaxed">
              Supercharge your IP attorneys with AI-assisted prior art search and automated preliminary infringement analyses.
            </p>
            <ul className="space-y-3 font-semibold text-slate-700">
              <li className="flex items-center gap-2"><CheckCircle2 className="w-5 h-5 text-blue-600" /> Deep semantic patent matching</li>
              <li className="flex items-center gap-2"><CheckCircle2 className="w-5 h-5 text-blue-600" /> Prior art discovery</li>
              <li className="flex items-center gap-2"><CheckCircle2 className="w-5 h-5 text-blue-600" /> Exportable compliance PDFs</li>
            </ul>
          </div>
        </div>

        <div className="mt-16 text-center">
          <Link href="/" className="inline-flex items-center gap-2 px-8 py-3.5 bg-blue-600 hover:bg-blue-700 text-white font-extrabold text-sm uppercase tracking-wider transition-all shadow-md hover:shadow-lg">
            Start Checking Now
          </Link>
        </div>
      </main>
    </div>
  );
}
