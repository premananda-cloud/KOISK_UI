import React, { createContext, useContext, useState, useRef } from 'react';

const KeyboardContext = createContext();

export function KeyboardProvider({ children }) {
  const [activeInput, setActiveInput] = useState(null);
  const inputRef = useRef(null);

  const focusInput = (ref) => {
    inputRef.current = ref;
    setActiveInput(ref);
  };

  const blurInput = () => {
    setActiveInput(null);
    inputRef.current = null;
  };

  const insertChar = (char) => {
    if (!inputRef.current) return;
    const start = inputRef.current.selectionStart;
    const end = inputRef.current.selectionEnd;
    const value = inputRef.current.value;
    const newValue = value.substring(0, start) + char + value.substring(end);
    inputRef.current.value = newValue;
    // Trigger React's onChange event manually
    const event = new Event('input', { bubbles: true });
    inputRef.current.dispatchEvent(event);
    // Move cursor after inserted char
    inputRef.current.setSelectionRange(start + char.length, start + char.length);
  };

  const handleBackspace = () => {
    if (!inputRef.current) return;
    const start = inputRef.current.selectionStart;
    const end = inputRef.current.selectionEnd;
    if (start === end && start > 0) {
      // Delete one character before cursor
      const value = inputRef.current.value;
      const newValue = value.substring(0, start - 1) + value.substring(end);
      inputRef.current.value = newValue;
      const event = new Event('input', { bubbles: true });
      inputRef.current.dispatchEvent(event);
      inputRef.current.setSelectionRange(start - 1, start - 1);
    } else if (start !== end) {
      // Delete selected range
      const value = inputRef.current.value;
      const newValue = value.substring(0, start) + value.substring(end);
      inputRef.current.value = newValue;
      const event = new Event('input', { bubbles: true });
      inputRef.current.dispatchEvent(event);
      inputRef.current.setSelectionRange(start, start);
    }
  };

  const handleClear = () => {
    if (!inputRef.current) return;
    inputRef.current.value = '';
    const event = new Event('input', { bubbles: true });
    inputRef.current.dispatchEvent(event);
  };

  const handleKeyPress = (key) => {
    if (key === 'Backspace') handleBackspace();
    else if (key === 'Clear') handleClear();
    else if (key === 'Close') blurInput();
    else if (key === ' ') insertChar(' ');
    else insertChar(key);
  };

  return (
    <KeyboardContext.Provider
      value={{
        activeInput,
        focusInput,
        blurInput,
        handleKeyPress,
      }}
    >
      {children}
    </KeyboardContext.Provider>
  );
}

export function useKeyboard() {
  return useContext(KeyboardContext);
}