import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './components/Dashboard';
import TicketList from './components/TicketList';
import TicketDetail from './components/TicketDetail';
import TicketForm from './components/TicketForm';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="tickets" element={<TicketList />} />
          <Route path="tickets/new" element={<TicketForm />} />
          <Route path="tickets/:id" element={<TicketDetail />} />
          <Route path="tickets/:id/edit" element={<TicketForm />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
