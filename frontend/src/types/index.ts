
export interface DisplayMessage {
  role: "user" | "assistant";
  content: string;
  citations: Citation[];
}

export interface Citation {
  source_url: string;
  source_description: string;
}

export interface LoadingIndicator {
  status: string;
  icon: "understanding" | "thinking" | "searching" | "documents" | "error";
}
