import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';

interface Client {
  id: string;
  name: string;
  email: string;
  phone?: string;
  age?: number;
  income?: number;
  occupation?: string;
  goals?: string;
  notes?: string;
  created_at: string;
  updated_at: string;
}

interface ClientContextType {
  currentClient: Client | null;
  clients: Client[];
  setCurrentClient: (client: Client | null) => void;
  loadClients: () => Promise<void>;
  createClient: (clientData: Partial<Client>) => Promise<Client | null>;
  isLoading: boolean;
}

const ClientContext = createContext<ClientContextType | undefined>(undefined);

export const useClient = () => {
  const context = useContext(ClientContext);
  if (context === undefined) {
    throw new Error('useClient must be used within a ClientProvider');
  }
  return context;
};

interface ClientProviderProps {
  children: ReactNode;
}

export const ClientProvider: React.FC<ClientProviderProps> = ({ children }) => {
  const [currentClient, setCurrentClient] = useState<Client | null>(null);
  const [clients, setClients] = useState<Client[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const loadClients = async () => {
    setIsLoading(true);
    try {
      const response = await fetch('http://localhost:8000/api/clients');
      const data = await response.json();
      
      if (data.success) {
        setClients(data.clients);
        // If no current client is selected and we have clients, select the first one
        if (!currentClient && data.clients.length > 0) {
          setCurrentClient(data.clients[0]);
        }
      } else {
        console.error('Failed to load clients:', data.error);
      }
    } catch (error) {
      console.error('Error loading clients:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const createClient = async (clientData: Partial<Client>): Promise<Client | null> => {
    setIsLoading(true);
    try {
      const response = await fetch('http://localhost:8000/api/clients', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(clientData),
      });
      
      const data = await response.json();
      
      if (data.success) {
        const newClient = data.client;
        setClients(prev => [...prev, newClient]);
        setCurrentClient(newClient);
        return newClient;
      } else {
        console.error('Failed to create client:', data.error);
        return null;
      }
    } catch (error) {
      console.error('Error creating client:', error);
      return null;
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadClients();
  }, []);

  const value: ClientContextType = {
    currentClient,
    clients,
    setCurrentClient,
    loadClients,
    createClient,
    isLoading,
  };

  return (
    <ClientContext.Provider value={value}>
      {children}
    </ClientContext.Provider>
  );
};
