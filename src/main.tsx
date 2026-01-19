import React from 'react'
import { createRoot } from 'react-dom/client'
import App from './app/App'
import './styles/tailwind.css'

const el = document.getElementById('root')
if (!el) throw new Error('Root element not found')

const root = createRoot(el)
root.render(<App />)
