import React, { useState } from 'react';
import { useClient } from '../contexts/ClientContext';
import { Button } from './ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { UserPlusIcon, UsersIcon } from 'lucide-react';
import { ClientDataForm } from './financial/ClientDataForm';

export const ClientSelector: React.FC = () => {
  const { currentClient, clients, setCurrentClient, createClient, isLoading } = useClient();
  const [showClientForm, setShowClientForm] = useState(false);

  const handleClientChange = (clientId: string) => {
    const selectedClient = clients.find(client => client.id === clientId);
    if (selectedClient) {
      setCurrentClient(selectedClient);
    }
  };

  const handleClientDataSubmit = async (clientData: any) => {
    const newClient = await createClient(clientData);
    if (newClient) {
      setShowClientForm(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 text-gray-400">
        <UsersIcon className="w-4 h-4" />
        <span className="text-sm">Loading clients...</span>
      </div>
    );
  }

  return (
    <>
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <UsersIcon className="w-4 h-4 text-gray-300" />
          <span className="text-sm text-gray-300">Client:</span>
        </div>
        
        <Select value={currentClient?.id || ''} onValueChange={handleClientChange}>
          <SelectTrigger className="w-48 bg-gray-700 border-gray-600 text-gray-100">
            <SelectValue placeholder="Select a client" />
          </SelectTrigger>
          <SelectContent className="bg-gray-800 border-gray-600">
            {clients.map((client) => (
              <SelectItem 
                key={client.id} 
                value={client.id}
                className="text-gray-100 hover:bg-gray-700"
              >
                {client.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Button
          onClick={() => setShowClientForm(true)}
          variant="outline"
          size="sm"
          className="gap-2 text-gray-300 border-gray-600 hover:bg-gray-700"
        >
          <UserPlusIcon className="w-4 h-4" />
          Add Client
        </Button>
      </div>

      {showClientForm && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-gradient-to-br from-gray-800 to-gray-900 border border-gray-600/50 p-8 rounded-2xl max-w-lg w-full shadow-2xl transform transition-all duration-300 scale-100">
            {/* Header */}
            <div className="flex justify-between items-center mb-6">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-blue-600 rounded-full flex items-center justify-center">
                  <UserPlusIcon className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h2 className="text-2xl font-bold text-gray-100">Add New Client</h2>
                  <p className="text-sm text-gray-400">Create a new client profile</p>
                </div>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowClientForm(false)}
                className="text-gray-400 hover:text-gray-200 hover:bg-gray-700/50 rounded-full w-8 h-8 p-0"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </Button>
            </div>
            
            {/* Form */}
            <div className="bg-gray-700/30 rounded-xl p-6 border border-gray-600/30">
              <ClientDataForm onSubmit={handleClientDataSubmit} />
            </div>
          </div>
        </div>
      )}
    </>
  );
};
