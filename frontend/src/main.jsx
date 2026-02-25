import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { AuthProvider } from './AuthContext'
import { ThemeProvider } from './contexts/ThemeContext'
import { DialogProvider } from './contexts/DialogContext'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
    <React.StrictMode>
        <BrowserRouter>
            <AuthProvider>
                <ThemeProvider>
                    <DialogProvider>
                        <App />
                    </DialogProvider>
                </ThemeProvider>
            </AuthProvider>
        </BrowserRouter>
    </React.StrictMode>
)
