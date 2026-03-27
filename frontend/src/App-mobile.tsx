import React from 'react';
import { Routes, Route } from 'react-router-dom';
import MobileLayout from './components/Mobile/MobileLayout';
import MobileChat from './components/Mobile/MobileChat';
import MobileHistory from './components/Mobile/MobileHistory';

function AppMobile() {
  return (
    <Routes>
      <Route path="/" element={<MobileLayout />}>
        <Route index element={<MobileChat />} />
        <Route path="history" element={<MobileHistory />} />
      </Route>
    </Routes>
  );
}

export default AppMobile;
