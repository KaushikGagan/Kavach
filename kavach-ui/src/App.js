import React, { createContext, useContext, useState } from 'react';
import Navbar from './components/Navbar';
import KYCPage from './pages/KYCPage';
import './index.css';

export const ThemeContext = createContext({ dark: true, toggle: () => {} });
export const useTheme = () => useContext(ThemeContext);

export default function App() {
  const [dark, setDark] = useState(true);

  return (
    <ThemeContext.Provider value={{ dark, toggle: () => setDark(d => !d) }}>
      <div className={dark ? 'theme-dark' : 'theme-light'}>
        <Navbar />
        <KYCPage />
      </div>
    </ThemeContext.Provider>
  );
}
