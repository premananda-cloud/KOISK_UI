import { useRef, useEffect } from 'react';
import { useKeyboard } from '../context/KeyboardContext';

export function useKeyboardInput() {
  const inputRef = useRef(null);
  const { focusInput } = useKeyboard();

  useEffect(() => {
    const handleFocus = () => focusInput(inputRef.current);
    const inputEl = inputRef.current;
    if (inputEl) {
      inputEl.addEventListener('focus', handleFocus);
    }
    return () => {
      if (inputEl) inputEl.removeEventListener('focus', handleFocus);
    };
  }, [focusInput]);

  return inputRef;
}