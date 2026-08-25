import { render, screen } from '@testing-library/react';
import Home from './page';

describe('Home Page', () => {
  it('renders the main title', () => {
    render(<Home />);
    expect(screen.getByText('Traffic Control System')).toBeInTheDocument();
  });

  it('renders feature cards', () => {
    render(<Home />);
    expect(screen.getByText('Network Solver')).toBeInTheDocument();
    expect(screen.getByText('ML Prediction')).toBeInTheDocument();
    expect(screen.getByText('Solver Comparison')).toBeInTheDocument();
  });
});