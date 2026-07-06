import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import SearchView from "@/components/search-view";
import AskView from "@/components/ask-view";
import CheckView from "@/components/check-view";
import { HealthBadge } from "@/components/health-badge";

export default function Home() {
  return (
    <main className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Compliance RAG</h1>
        <HealthBadge/>
      </div>
      <Tabs defaultValue="search">
        <TabsList>
          <TabsTrigger value="search">Search</TabsTrigger>
          <TabsTrigger value="ask">
            Ask
          </TabsTrigger>
          <TabsTrigger value="check">
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
