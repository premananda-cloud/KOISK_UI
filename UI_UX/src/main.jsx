import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App.jsx'
import './index.css'

// i18n must init before app renders
import './modules/language/i18n.js'

import { KeyboardProvider } from './context/KeyboardContext.jsx' // FIX: wrap app

const root = ReactDOM.createRoot(document.getElementById('root'))

root.render(
  <React.StrictMode>
    <BrowserRouter>
      <KeyboardProvider>
        <App />
      </KeyboardProvider>
    </BrowserRouter>
  </React.StrictMode>
)

// Hide the splash screen once React has rendered
// requestAnimationFrame ensures the first paint has happened
requestAnimationFrame(() => {
  requestAnimationFrame(() => {
    const splash = document.getElementById('app-splash')
    if (splash) {
      splash.classList.add('hidden')
      // Remove from DOM after transition ends (0.35s defined in index.html)
      splash.addEventListener('transitionend', () => splash.remove(), { once: true })
    }
  })
})

