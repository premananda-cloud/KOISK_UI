import React, { useState, useEffect } from 'react';

// Basic alphanumeric layout (you can extend with symbols, shift, etc.)
const LAYOUT = [
  ['1','2','3','4','5','6','7','8','9','0'],
  ['q','w','e','r','t','y','u','i','o','p'],
  ['a','s','d','f','g','h','j','k','l'],
  ['z','x','c','v','b','n','m'],
  [' ', 'Backspace', 'Clear', 'Close']
];

export default function Keyboard({ onKeyPress, onClose }) {
  const handleClick = (key) => {
    if (key === 'Close') {
      onClose?.();
      return;
    }
    onKeyPress?.(key);
  };

  return (
    <div className="fixed bottom-0 left-0 right-0 bg-gray-800 p-4 shadow-2xl z-50">
      <div className="flex flex-col items-center gap-2">
        {LAYOUT.map((row, i) => (
          <div key={i} className="flex justify-center gap-1">
            {row.map((key) => (
              <button
                key={key}
                onClick={() => handleClick(key)}
                className={`px-4 py-3 text-lg font-medium rounded ${
                  key === ' '
                    ? 'w-64 bg-blue-600 hover:bg-blue-700'
                    : key === 'Backspace' || key === 'Clear' || key === 'Close'
                    ? 'bg-red-600 hover:bg-red-700 w-24'
                    : 'bg-gray-600 hover:bg-gray-700 w-12'
                } text-white transition`}
              >
                {key === ' ' ? '␣ Space' : key}
              </button>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}