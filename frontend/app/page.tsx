import { Tabs, TabsContent, TabsIndicator, TabsList, TabsTrigger } from "@/components/ui/tabs";
import SearchView from "@/components/search-view";
import AskView from "@/components/ask-view";
import CheckView from "@/components/check-view";
import { HealthBadge } from "@/components/health-badge";

// The sliding indicator draws the active state, so triggers stay transparent.
const TRIGGER =
  "relative z-10 min-h-11 px-4 font-ui data-active:bg-transparent data-active:shadow-none dark:data-active:border-transparent dark:data-active:bg-transparent";

// Panels stay mounted so switching modes keeps results and doesn't cancel an
// answer that is still streaming.
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
        {/* Mode switch: the ink sheet slides to the chosen mode (Base UI
            measures the active tab for TabsIndicator). */}
        <TabsList aria-label="Mode" className="relative min-h-11">
          <TabsTrigger value="search" className={TRIGGER}>
            Search
          </TabsTrigger>
          <TabsTrigger value="ask" className={TRIGGER}>
            Ask
          </TabsTrigger>
          <TabsTrigger value="check" className={TRIGGER}>
            Check
          </TabsTrigger>
          <TabsIndicator className="rounded-md border border-border bg-raised shadow-xs dark:border-transparent" />
        </TabsList>
        <TabsContent value="search" keepMounted className="pt-4">
          <SearchView />
        </TabsContent>
        <TabsContent value="ask" keepMounted className="pt-4">
          <AskView />
        </TabsContent>
        <TabsContent value="check" keepMounted className="pt-4">
          <CheckView />
        </TabsContent>
      </Tabs>
    </main>
  );
}
