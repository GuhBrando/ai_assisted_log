import { useQuery } from '@tanstack/react-query';

// Rótulo da API usada pelo processo principal, para distinguir dados reais do mock.
export function useApiTargetLabel(): string {
  const target = useQuery({
    queryKey: ['api-target'],
    queryFn: async () => {
      const result = await window.logApi.apiTarget();
      if (!result.ok) throw new Error(result.error.message);
      return result.data;
    },
    staleTime: Infinity,
  });
  if (!target.data) return '';
  const { host } = new URL(target.data.url);
  return `${target.data.mock ? 'Mock Prism' : 'API local'} · ${host}`;
}
