import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import SearchView from "@/components/search-view";
import AskView from "@/components/ask-view";
import CheckView from "@/components/check-view";
import { HealthBadge } from "@/components/health-badge";

export default function Home() {
  return (
    <main className="space-y-6">
      <div className="flex items-center justify-between gap-4">
        {/* DESIGN.md `display-xl`: 52 / 1.05, masthead only. Never below 24px —
            Didot is high-contrast and its hairlines break at small sizes. */}
        <h1 className="font-display text-[2rem] leading-[1.05] sm:text-[3.25rem]">
          Compliance RAG
        </h1>
        <HealthBadge />
      </div>
      <Tabs defaultValue="search">
        <TabsList className="min-h-11">
          <TabsTrigger value="search" className="min-h-11 px-3">
            Search
          </TabsTrigger>
          <TabsTrigger value="ask" className="min-h-11 px-3">
            Ask
          </TabsTrigger>
          <TabsTrigger value="check" className="min-h-11 px-3">
            Check
          </TabsTrigger>
        </TabsList>
        <TabsContent value="search" className="pt-4">
          <SearchView />
        </TabsContent>
        <TabsContent value="ask" className="pt-4">
          <AskView />
        </TabsContent>
        <TabsContent value="check" className="pt-4">
          <CheckView />
        </TabsContent>
      </Tabs>
    </main>
  );
}
