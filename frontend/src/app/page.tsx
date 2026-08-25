'use client';

import Link from 'next/link';

export default function Home() {
  return (
    <main className="min-h-screen">
      <header className="bg-primary-600 text-white shadow-lg">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <h1 className="text-4xl font-bold">Traffic Control System</h1>
          <p className="mt-2 text-primary-100 max-w-2xl">
            Multi-language traffic flow optimization with Python, Rust, and TypeScript
          </p>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid md:grid-cols-3 gap-8 mb-16">
          <Link href="/solver" className="group block p-6 bg-white dark:bg-gray-800 rounded-xl shadow-md hover:shadow-xl transition-shadow border border-gray-200 dark:border-gray-700">
            <div className="text-4xl mb-3">Tools</div>
            <h3 className="text-xl font-semibold mb-2 group-hover:text-primary-600 dark:group-hover:text-primary-400 transition-colors">
              Network Solver
            </h3>
            <p className="text-gray-600 dark:text-gray-300">
              Build networks, select solvers (RREF, LP, MILP, Max Flow), and visualize flows in real-time.
            </p>
          </Link>

          <Link href="/ml" className="group block p-6 bg-white dark:bg-gray-800 rounded-xl shadow-md hover:shadow-xl transition-shadow border border-gray-200 dark:border-gray-700">
            <div className="text-4xl mb-3">ML</div>
            <h3 className="text-xl font-semibold mb-2 group-hover:text-primary-600 dark:group-hover:text-primary-400 transition-colors">
              ML Prediction
            </h3>
            <p className="text-gray-600 dark:text-gray-300">
              Train models on SUMO simulation data, predict traffic flows, and compare model performance.
            </p>
          </Link>

          <Link href="/compare" className="group block p-6 bg-white dark:bg-gray-800 rounded-xl shadow-md hover:shadow-xl transition-shadow border border-gray-200 dark:border-gray-700">
            <div className="text-4xl mb-3">Chart</div>
            <h3 className="text-xl font-semibold mb-2 group-hover:text-primary-600 dark:group-hover:text-primary-400 transition-colors">
              Solver Comparison
            </h3>
            <p className="text-gray-600 dark:text-gray-300">
              Benchmark Python, Rust, and TypeScript implementations side-by-side with performance metrics.
            </p>
          </Link>
        </div>

        <section className="mb-16">
          <h2 className="text-3xl font-bold mb-8 text-center">Features</h2>
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {[
              { icon: 'Perf', title: 'High Performance', desc: 'Rust implementation 10-50x faster than Python' },
              { icon: 'Multi', title: 'Multi-Language', desc: 'Python, Rust, and TypeScript implementations' },
              { icon: 'Auth', title: 'Secure API', desc: 'JWT authentication with role-based access' },
              { icon: 'DB', title: 'Persistent Storage', desc: 'MongoDB for network and model persistence' },
              { icon: 'ML', title: 'ML Integration', desc: 'Train and serve traffic prediction models' },
              { icon: 'UI', title: 'Interactive UI', desc: 'React Flow network editor with live visualization' },
              { icon: 'Test', title: 'Well Tested', desc: 'Property-based tests, integration tests, benchmarks' },
              { icon: 'Docker', title: 'Containerized', desc: 'Docker and docker-compose for easy deployment' },
            ].map((feature, i) => (
              <div key={i} className="p-6 bg-white dark:bg-gray-800 rounded-xl shadow-md border border-gray-200 dark:border-gray-700">
                <div className="text-lg font-mono font-bold mb-3 text-primary-600 dark:text-primary-400">{feature.icon}</div>
                <h4 className="font-semibold mb-1">{feature.title}</h4>
                <p className="text-sm text-gray-600 dark:text-gray-300">{feature.desc}</p>
              </div>
            ))}
          </div>
        </section>

        <section>
          <h2 className="text-3xl font-bold mb-8 text-center">Tech Stack</h2>
          <div className="flex flex-wrap justify-center gap-4">
            {[
              'Python 3.11+',
              'FastAPI',
              'NumPy/SciPy',
              'scikit-learn',
              'Rust 1.75+',
              'nalgebra',
              'petgraph',
              'TypeScript 5.0+',
              'React 18',
              'Next.js 14',
              'React Flow',
              'Tailwind CSS',
              'MongoDB',
              'Docker',
              'GitHub Actions',
            ].map((tech, i) => (
              <span key={i} className="px-4 py-2 bg-primary-100 dark:bg-primary-900 text-primary-800 dark:text-primary-200 rounded-full text-sm font-medium">
                {tech}
              </span>
            ))}
          </div>
        </section>
      </div>

      <footer className="bg-gray-100 dark:bg-gray-900 border-t border-gray-200 dark:border-gray-800 mt-16">
        <div className="max-w-7xl mx-auto px-4 py-8 text-center text-gray-600 dark:text-gray-400">
          <p>Built for portfolio demonstration — showcasing multi-language systems engineering</p>
          <p className="mt-2">
            <a href="https://github.com/yourusername/traffic-control-system" className="text-primary-600 hover:underline" target="_blank" rel="noopener noreferrer">
              View on GitHub
            </a>
          </p>
        </div>
      </footer>
    </main>
  );
}