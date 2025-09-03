"use client";

import { useEffect, useState } from "react";
import { DisplayMessage, LoadingIndicator, Citation } from "../types";

const INITIAL_MESSAGE = "Hello! I'm your financial assistant. I can help you analyze client data, review financial documents, and provide investment guidance. How can I assist you today?";

export default function useFinancialApp() {
  const initialAssistantMessage: DisplayMessage = {
    role: "assistant",
    content: INITIAL_MESSAGE,
    citations: [],
  };

  const [messages, setMessages] = useState<DisplayMessage[]>([initialAssistantMessage]);
  const [isLoading, setIsLoading] = useState(false);
  const [indicatorState, setIndicatorState] = useState<LoadingIndicator[]>([]);
  const [input, setInput] = useState("");
  const [conversationId, setConversationId] = useState<string>("");

  // Generate conversation ID on mount
  useEffect(() => {
    setConversationId(crypto.randomUUID());
  }, []);

  const addUserMessage = (input: string) => {
    const newUserMessage: DisplayMessage = {
      role: "user",
      content: input,
      citations: [],
    };
    setMessages((prevMessages) => [...prevMessages, newUserMessage]);
    return newUserMessage;
  };

  const addAssistantMessage = (content: string, citations: Citation[]) => {
    const newAssistantMessage: DisplayMessage = {
      role: "assistant",
      content,
      citations,
    };
    setMessages((prevMessages) => [...prevMessages, newAssistantMessage]);
    return newAssistantMessage;
  };

  const fetchAssistantResponse = async (allMessages: DisplayMessage[]) => {
    const response = await fetch("http://localhost:8000/api/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        message: allMessages[allMessages.length - 1].content, // Send just the last message
        conversation_id: conversationId
      }),
    });

    if (!response.ok) {
      throw new Error("Failed to send message");
    }

    return response;
  };

  const handleStreamedMessage = (streamedMessage: any) => {
    setIndicatorState([]);
    setMessages((prevMessages) => {
      const updatedMessages = [...prevMessages];
      const lastMessage = updatedMessages[updatedMessages.length - 1];

      if (lastMessage && lastMessage.role === "assistant") {
        updatedMessages[updatedMessages.length - 1] = {
          ...lastMessage,
          content: streamedMessage.message.content,
          citations: streamedMessage.message.citations,
        };
      } else {
        updatedMessages.push({
          role: "assistant",
          content: streamedMessage.message.content,
          citations: streamedMessage.message.citations,
        });
      }

      return updatedMessages;
    });
  };

  const handleStreamedLoading = (streamedLoading: any) => {
    setIndicatorState((prevIndicatorState) => [
      ...prevIndicatorState,
      streamedLoading.indicator,
    ]);
  };

  const handleStreamedError = (streamedError: any) => {
    setIndicatorState((prevIndicatorState) => [
      ...prevIndicatorState,
      { ...streamedError.indicator, icon: "error" },
    ]);
  };

  const processStreamedResponse = async (response: Response) => {
    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error("No reader available");
    }

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const payload = new TextDecoder().decode(value);
      const payloads = payload.split("\n").filter((p) => p.trim() !== "");

      for (const payloadLine of payloads) {
        try {
          const parsedPayload = JSON.parse(payloadLine);

          if (parsedPayload.type === "message") {
            handleStreamedMessage(parsedPayload);
          } else if (parsedPayload.type === "loading") {
            handleStreamedLoading(parsedPayload);
          } else if (parsedPayload.type === "error") {
            handleStreamedError(parsedPayload);
          }
        } catch (e) {
          console.warn("Failed to parse payload:", payloadLine);
        }
      }
    }
  };

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!input.trim()) return;
    
    setIndicatorState([]);
    setIsLoading(true);
    setInput("");
    const newUserMessage = addUserMessage(input);

    setTimeout(() => {
      setIndicatorState([
        {
          status: "Analyzing your request",
          icon: "understanding",
        },
      ]);
    }, 600);

    try {
      const response = await fetchAssistantResponse([
        ...messages,
        newUserMessage,
      ]);
      
      const data = await response.json();
      if (data.message && data.message.content) {
        addAssistantMessage(data.message.content, data.message.citations || []);
      } else {
        addAssistantMessage("I encountered an error processing your request. Please try again.", []);
      }
    } catch (error) {
      console.error("Error:", error);
      addAssistantMessage("I encountered an error processing your request. Please try again.", []);
    } finally {
      setIsLoading(false);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setInput(e.target.value);
  };

  const clearMessages = () => {
    setMessages([initialAssistantMessage]);
    setConversationId(crypto.randomUUID());
  };

  return {
    messages,
    handleInputChange,
    handleSubmit,
    indicatorState,
    input,
    isLoading,
    setMessages,
    clearMessages,
    conversationId,
  };
}
