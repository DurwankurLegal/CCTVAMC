import { useSearchParams } from "react-router-dom";

export interface ParsedParams {
  status: string | null;
  priority: string | null;
  category: string | null;
  customer: string | null;
  contract_number: string | null;
  overdue: boolean;
  notes: string | null;
}

/**
 * Custom hook to extract and normalize common search query parameters 
 * carried over from the Smart Dashboard navigation events.
 */
export function useParsedSearchParams(): ParsedParams {
  const [searchParams] = useSearchParams();
  
  return {
    status: searchParams.get("status"),
    priority: searchParams.get("priority"),
    category: searchParams.get("category"),
    customer: searchParams.get("customer"),
    contract_number: searchParams.get("contract_number"),
    overdue: searchParams.get("overdue") === "true",
    notes: searchParams.get("notes"),
  };
}

/**
 * Utility to construct query parameter strings cleanly.
 */
export function buildQueryString(params: Partial<ParsedParams>): string {
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== null && value !== undefined) {
      searchParams.set(key, String(value));
    }
  });
  const qs = searchParams.toString();
  return qs ? `?${qs}` : "";
}
