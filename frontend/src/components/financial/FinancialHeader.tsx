'use client';

import { Button } from '../ui/button';
import { EraserIcon } from 'lucide-react';
import { motion } from 'framer-motion';
import { ThemeToggle } from '../ThemeToggle';
import { ClientSelector } from '../ClientSelector';
import { useClient } from '../../contexts/ClientContext';

const AILogo = () => (
  <motion.div
    whileHover={{ scale: 1.05 }}
    transition={{ type: 'spring', stiffness: 300, damping: 15 }}
    className='w-12 h-12 relative'
  >
    <div className='w-12 h-12 bg-blue-600 rounded-full flex items-center justify-center'>
      <span className='text-white font-bold text-xl'>FA</span>
    </div>
    <div className='w-2 h-2 rounded-full bg-green-500 absolute -bottom-0.5 -right-0.5' />
  </motion.div>
);

interface FinancialHeaderProps {
  clearMessages: () => void;
  onGenerateReport?: () => void;
}

export default function FinancialHeader({ clearMessages, onGenerateReport }: FinancialHeaderProps) {
  const { currentClient } = useClient();

  return (
    <>
      <div className='z-10 fixed top-0 w-full bg-gray-800 border-b border-gray-700 shadow-lg'>
        <div className='max-w-4xl mx-auto px-6 py-4'>
          <div className='flex items-center justify-between'>
            <div className='flex items-center gap-3'>
              <AILogo />
              <div>
                <h1 className='text-xl font-semibold text-gray-100'>Financial Assistant</h1>
                <p className='text-sm text-gray-400'>
                  {currentClient ? `Working with: ${currentClient.name}` : 'Your AI-powered financial advisor'}
                </p>
              </div>
            </div>

            <div className='flex items-center gap-2'>
              <ClientSelector />
              
              {onGenerateReport && (
                <Button
                  onClick={onGenerateReport}
                  size='sm'
                  className='gap-2 bg-blue-600 hover:bg-blue-700 text-white'
                >
                  📊 Generate Report
                </Button>
              )}
              
              <ThemeToggle />

              <Button
                onClick={clearMessages}
                variant='outline'
                size='sm'
                className='gap-2 text-gray-300 border-gray-600 hover:bg-gray-700'
              >
                <EraserIcon className='w-4 h-4' />
                Clear
              </Button>
            </div>
          </div>
        </div>
      </div>

    </>
  );
}