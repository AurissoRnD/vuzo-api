import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { AuthProvider } from './contexts/AuthContext'
import ProtectedRoute from './components/ProtectedRoute'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import ApiKeys from './pages/ApiKeys'
import Usage from './pages/Usage'
import Billing from './pages/Billing'
import Models from './pages/Models'
import Docs from './pages/Docs'
import Admin from './pages/Admin'

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Admin portal — standalone, manages its own auth */}
          <Route path="/admin" element={<Admin />} />

          <Route
            element={
              <ProtectedRoute>
                <Layout />
              </ProtectedRoute>
            }
          >
            <Route path="/" element={<Dashboard />} />
            <Route path="/api-keys" element={<ApiKeys />} />
            <Route path="/usage" element={<Usage />} />
            <Route path="/billing" element={<Billing />} />
            <Route path="/models" element={<Models />} />
            <Route path="/docs" element={<Docs />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}
