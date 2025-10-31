import React, { useState, useEffect } from 'react';
import { MapContainer, TileLayer, CircleMarker, Popup } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import ExplainerSections from './ExplainerSections';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';

function App() {
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [selectedZip, setSelectedZip] = useState(null);
  const [affordabilityData, setAffordabilityData] = useState([]);
  const [dashboardStats, setDashboardStats] = useState(null);
  const [dataVintage, setDataVintage] = useState('ACS 2018–2022 5-year'); // Default, will be fetched
  const [snapFilter, setSnapFilter] = useState(false);
  const [loading, setLoading] = useState(true);
  const [activeView, setActiveView] = useState('what-is-this');
  const [scrapingStatus, setScrapingStatus] = useState(null);
  const [mlPredictions, setMlPredictions] = useState(null);
  const [riskPredictions, setRiskPredictions] = useState([]);
  const [showAtRiskOnly, setShowAtRiskOnly] = useState(false);
  const [foodBasket, setFoodBasket] = useState([]);

  const fetchScrapingStatus = async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/test-scraping`);
      const result = await response.json();
      setScrapingStatus(result);
    } catch (error) {
      console.error('Error fetching scraping status:', error);
    }
  };

  const fetchMlPredictions = async () => {
    try {
      console.log('🤖 Fetching ML predictions from:', `${BACKEND_URL}/api/ml/predict-risk`);
      const response = await fetch(`${BACKEND_URL}/api/ml/predict-risk`);
      console.log('🤖 ML API response status:', response.status);
      
      if (!response.ok) {
        console.error('🤖 ML API response not OK:', response.status, response.statusText);
        return;
      }
      
      const result = await response.json();
      console.log('🤖 ML API result:', result);
      console.log('🤖 ML predictions count:', result.predictions ? result.predictions.length : 'No predictions property');
      
      setRiskPredictions(result.predictions || []);
      console.log('🤖 Risk predictions state updated');
    } catch (error) {
      console.error('🤖 Error fetching ML predictions:', error);
    }
  };

  const fetchData = async () => {
    try {
      setLoading(true);
      
      // Fetch affordability data (all ZIP codes for map)
      const affordabilityResponse = await fetch(`${BACKEND_URL}/api/affordability?limit=1000`);
      const affordabilityResult = await affordabilityResponse.json();
      setAffordabilityData(affordabilityResult.data || affordabilityResult);

      // Fetch food basket
      const basketResponse = await fetch(`${BACKEND_URL}/api/food-basket`);
      const basketResult = await basketResponse.json();
      setFoodBasket(basketResult.items);

      // Fetch dashboard stats
      const statsResponse = await fetch(`${BACKEND_URL}/api/stats`);
      const statsResult = await statsResponse.json();
      setDashboardStats(statsResult);

      // Fetch configuration including data vintage
      try {
        const configResponse = await fetch(`${BACKEND_URL}/api/config`);
        const configResult = await configResponse.json();
        if (configResult.data_vintage_label) {
          setDataVintage(configResult.data_vintage_label);
        }
      } catch (configError) {
        console.error('Error fetching config:', configError);
        // Keep default data vintage if config fetch fails
      }

    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = async (query) => {
    console.log('🔍 Search triggered with query:', query);
    if (query.length < 2) {
      console.log('🔍 Query too short, clearing results');
      setSearchResults([]);
      return;
    }
    
    try {
      const searchUrl = `${BACKEND_URL}/api/search-zipcodes?q=${encodeURIComponent(query)}&limit=10`;
      console.log('🔍 Fetching from URL:', searchUrl);
      
      const response = await fetch(searchUrl);
      console.log('🔍 Search response status:', response.status);
      
      if (!response.ok) {
        console.error('🔍 Search API response not OK:', response.status, response.statusText);
        setSearchResults([]);
        return;
      }
      
      const results = await response.json();
      console.log('🔍 Search results received:', results);
      console.log('🔍 Search results count:', Array.isArray(results) ? results.length : 'Not an array');
      
      setSearchResults(results);
      console.log('🔍 Search results state updated');
    } catch (error) {
      console.error('🔍 Error searching:', error);
      setSearchResults([]);
    }
  };

  const triggerScraping = async (zipCode = null) => {
    try {
      const endpoint = zipCode ? `/api/scrape/${zipCode}` : '/api/scrape-all';
      const response = await fetch(`${BACKEND_URL}${endpoint}`, { method: 'POST' });
      const result = await response.json();
      
      if (result.success || result.items_found) {
        alert(`Scraping successful! ${result.message || 'Data updated.'}`);
        fetchData();
        fetchScrapingStatus();
      } else {
        alert(`Scraping failed: ${result.error || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('Error during scraping:', error);
      alert('Scraping failed: Network error');
    }
  };

  const handleZipSelect = async (zipData) => {
    // Fetch complete ZIP data for the selected ZIP
    try {
      const response = await fetch(`${BACKEND_URL}/api/affordability/${zipData.zip_code}`);
      const completeZipData = await response.json();
      setSelectedZip(completeZipData);
      setSearchResults([]);
      setSearchQuery('');
    } catch (error) {
      console.error('Error fetching complete ZIP data:', error);
      // Fallback to basic search data
      setSelectedZip(zipData);
      setSearchResults([]);
      setSearchQuery('');
    }
  };

  const getColorByScore = (score) => {
    // Updated thresholds for ACS 2019–2023 5-year data (low % = green)
    if (score >= 4.0) return '#b91c1c';  // Muted crimson - Food Desert Risk (≥4.0%)
    if (score >= 3.0) return '#ea580c';  // Burnt orange - Moderate Access (3.0-4.0%)
    if (score >= 1.5) return '#f59e0b';  // Amber - Good Access (1.5-3.0%)
    return '#059669'; // Rich emerald - Excellent Access (<1.5%)
  };


  // Debounced search
  useEffect(() => {
    const timeoutId = setTimeout(() => {
      if (searchQuery) {
        handleSearch(searchQuery);
      } else {
        setSearchResults([]);
      }
    }, 300);
    
    return () => clearTimeout(timeoutId);
  }, [searchQuery]);

  // Fetch data on component mount
  useEffect(() => {
    fetchData();
    fetchScrapingStatus();
    fetchMlPredictions();
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0B0C0E] text-slate-100 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-emerald-500 mx-auto mb-4"></div>
          <p className="text-xl font-semibold">Loading NJ Food Access Data...</p>
          <p className="text-sm text-slate-400">Initializing comprehensive ZIP code analysis...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0B0C0E] text-slate-100">
      {/* Header */}
      <header className="bg-[#101010] text-slate-100 border-b border-emerald-800/40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="flex flex-col md:flex-row md:items-center justify-between">
            <div className="flex items-center space-x-4">
              <div>
                <h1 className="text-3xl md:text-4xl font-bold tracking-tight">Garden State Grocery Gap</h1>
                <p className="text-xl text-slate-400 mt-2">Food Access & Affordability Dashboard for New Jersey</p>
              </div>
            </div>
            
            <div className="mt-6 md:mt-0 flex flex-col items-end space-y-3">
              <div className="flex items-center space-x-4">
                <div className="rounded-lg px-4 py-2 bg-[#131517] border border-emerald-900/40">
                  <div className="text-xs text-slate-400">Data Source</div>
                  <div className="text-sm font-medium text-slate-100">Census Data (2018–2022)</div>
                  <div className="text-xs text-emerald-400/80 mt-1">{dataVintage}</div>
                </div>
              </div>
              
              <p className="text-slate-400 text-sm">
                {dashboardStats ? (
                  <>Analyzing <span className="font-bold text-slate-100">{dashboardStats.total_zip_codes}</span> ZIP codes across NJ</>
                ) : (
                  <>Analyzing <span className="font-bold text-slate-100">734</span> ZIP codes across NJ</>
                )}
              </p>
            </div>
          </div>
          
          {/* Navigation Tabs */}
          <div className="mt-8 flex flex-wrap gap-3">
            <button
              onClick={() => setActiveView('what-is-this')}
              className={`px-6 py-3 rounded-lg font-medium transition-colors duration-200 border ${
                activeView === 'what-is-this'
                  ? 'bg-emerald-600 text-white border-emerald-500 shadow'
                  : 'bg-[#131517] text-slate-200 border-emerald-900/30 hover:border-emerald-700/50 hover:text-white'
              }`}
            >
              What Is This?
            </button>
            
            <button
              onClick={() => setActiveView('interactive-map')}
              className={`px-6 py-3 rounded-lg font-medium transition-colors duration-200 border ${
                activeView === 'interactive-map'
                  ? 'bg-emerald-600 text-white border-emerald-500 shadow'
                  : 'bg-[#131517] text-slate-200 border-emerald-900/30 hover:border-emerald-700/50 hover:text-white'
              }`}
            >
              ZIP Code Explorer
            </button>
            
            <button
              onClick={() => setActiveView('risk-prediction')}
              className={`px-6 py-3 rounded-lg font-medium transition-colors duration-200 border ${
                activeView === 'risk-prediction'
                  ? 'bg-emerald-600 text-white border-emerald-500 shadow'
                  : 'bg-[#131517] text-slate-200 border-emerald-900/30 hover:border-emerald-700/50 hover:text-white'
              }`}
            >
              AI Risk Assessment
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {activeView === 'what-is-this' && <ExplainerSections />}

        {activeView === 'interactive-map' && (
          <div className="space-y-8">
            {/* Search Section */}
            <div className="bg-[#101315] rounded-xl p-8 shadow-lg border border-emerald-900/30">
              <div className="text-center mb-8">
                <h2 className="text-3xl font-bold text-slate-100 mb-3">Explore New Jersey ZIP Codes</h2>
                <p className="text-lg text-slate-400">Search by ZIP code, city, or county to view detailed food access information</p>
              </div>
              
              <div className="max-w-2xl mx-auto relative">
                <input
                  type="text"
                  placeholder="Search by ZIP code, city, or county..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full px-6 py-4 text-lg bg-[#0F1113] text-slate-100 placeholder-slate-500 border-2 border-emerald-900/30 rounded-lg focus:border-emerald-500 focus:outline-none transition-colors"
                />
                
                {/* Search Results Dropdown */}
                {searchResults.length > 0 && activeView === 'interactive-map' && (
                  <div className="absolute top-full left-0 right-0 bg-[#0F1113] text-slate-100 border border-emerald-900/30 rounded-lg mt-2 shadow-xl z-50 max-h-96 overflow-y-auto">
                    {searchResults.map((result) => (
                      <div
                        key={result.zip_code}
                        className="p-4 hover:bg-[#131517] cursor-pointer border-b border-emerald-900/20 last:border-b-0 transition-colors"
                        onClick={() => handleZipSelect(result)}
                      >
                        <div className="flex justify-between items-center">
                          <div>
                            <span className="font-semibold text-lg text-slate-100">{result.zip_code}</span>
                            <span className="text-slate-400 ml-3">{result.city}, {result.county} County</span>
                          </div>
                          <div className="flex items-center space-x-3">
                            <span className="px-3 py-1 bg-[#131517] text-slate-200 border border-emerald-900/30 rounded-full text-sm font-medium">
                              {result.affordability_score != null ? `${result.affordability_score}%` : 'Loading...'}
                            </span>
                            <div
                              className="w-4 h-4 rounded-full border-2 border-[#0F1113] shadow-md"
                              style={{ backgroundColor: getColorByScore(result.affordability_score) }}
                            ></div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
                
                <div className="flex items-center justify-center mt-6">
                  <label className="flex items-center space-x-3 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={snapFilter}
                      onChange={(e) => setSnapFilter(e.target.checked)}
                      className="w-5 h-5 text-emerald-500 bg-[#0F1113] border-2 border-emerald-900/40 rounded focus:ring-emerald-600 focus:ring-2"
                    />
                    <span className="text-lg font-medium text-slate-200">Show SNAP-Eligible Items Only</span>
                  </label>
                </div>
              </div>
            </div>

            {/* Affordability Score Legend */}
            <div className="bg-[#101315] rounded-xl p-8 shadow-lg border border-emerald-900/30">
              <h3 className="text-2xl font-bold text-slate-100 mb-6 text-center">Affordability Score Guide</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="text-center p-4 bg-[#0F1113] border-2 border-emerald-900/40 rounded-lg">
                  <div className="w-4 h-4 rounded-full mx-auto mb-2" style={{ backgroundColor: '#059669' }}></div>
                  <div className="font-bold text-emerald-400">Excellent Access</div>
                  <div className="text-sm text-emerald-300">Under 1.5%</div>
                  <div className="text-xs text-slate-400 mt-1">Data: {dataVintage}</div>
                </div>
                <div className="text-center p-4 bg-[#0F1113] border-2 border-emerald-900/40 rounded-lg">
                  <div className="w-4 h-4 rounded-full mx-auto mb-2" style={{ backgroundColor: '#f59e0b' }}></div>
                  <div className="font-bold text-amber-300">Good Access</div>
                  <div className="text-sm text-amber-300">1.5% - 3.0%</div>
                  <div className="text-xs text-slate-400 mt-1">Data: {dataVintage}</div>
                </div>
                <div className="text-center p-4 bg-[#0F1113] border-2 border-emerald-900/40 rounded-lg">
                  <div className="w-4 h-4 rounded-full mx-auto mb-2" style={{ backgroundColor: '#ea580c' }}></div>
                  <div className="font-bold text-orange-300">Moderate Access</div>
                  <div className="text-sm text-orange-300">3.0% - 4.0%</div>
                  <div className="text-xs text-slate-400 mt-1">Data: {dataVintage}</div>
                </div>
                <div className="text-center p-4 bg-[#0F1113] border-2 border-emerald-900/40 rounded-lg">
                  <div className="w-4 h-4 rounded-full mx-auto mb-2" style={{ backgroundColor: '#b91c1c' }}></div>
                  <div className="font-bold text-red-300">Food Desert Risk</div>
                  <div className="text-sm text-red-300">4.0%+</div>
                  <div className="text-xs text-slate-400 mt-1">Data: {dataVintage}</div>
                </div>
              </div>
              <p className="text-center text-slate-400 mt-6 text-lg">
                Higher scores indicate worse affordability (food costs more relative to local income)
              </p>
            </div>

            {/* Selected ZIP Details */}
            {selectedZip && (
              <div className="bg-[#101315] rounded-xl p-8 shadow-lg border border-emerald-900/30">
                <div className="flex justify-between items-start mb-8">
                  <div>
                    <h3 className="text-3xl font-bold text-slate-100">ZIP {selectedZip.zip_code}</h3>
                    <p className="text-xl text-slate-400 mt-2">{selectedZip.city}, {selectedZip.county} County</p>
                  </div>
                  <button
                    onClick={() => setSelectedZip(null)}
                    className="p-2 text-slate-400 hover:text-white hover:bg-[#131517] rounded-lg transition-colors"
                  >
                    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
                
                <div className="grid md:grid-cols-2 gap-8">
                  {/* Affordability Score */}
                  <div className="text-center p-8 bg-[#0F1113] rounded-xl border-2 border-emerald-900/40">
                    <div className="text-sm font-medium text-emerald-400 mb-2">AFFORDABILITY SCORE</div>
                    <div className="text-4xl font-bold mb-2" style={{ color: getColorByScore(selectedZip.affordability_score || 0) }}>
                      {selectedZip.affordability_score != null ? `${selectedZip.affordability_score}%` : 'Loading...'}
                    </div>
                    <div className="text-sm text-slate-300 font-medium">
                      {selectedZip.classification || 'Loading...'}
                    </div>
                    <div className="text-xs text-slate-400 mt-2">
                      Data: {dataVintage}
                    </div>
                  </div>
                  
                  {/* Key Statistics */}
                  <div className="grid grid-cols-2 gap-4">
                    <div className="p-4 bg-[#0F1113] rounded-lg border border-emerald-900/40">
                      <div className="text-sm font-medium text-emerald-300">Basket Cost</div>
                      <div className="text-2xl font-bold text-emerald-400">
                        ${selectedZip.basket_cost != null ? selectedZip.basket_cost.toFixed(2) : 'Loading...'}
                      </div>
                    </div>
                    <div className="p-4 bg-[#0F1113] rounded-lg border border-emerald-900/40">
                      <div className="text-sm font-medium text-slate-300">Median Income</div>
                      <div className="text-2xl font-bold text-slate-100">
                        ${selectedZip.median_income != null ? (selectedZip.median_income / 1000).toFixed(0) : 'Loading...'}k
                      </div>
                      <div className="text-xs text-slate-400 mt-1">
                        {dataVintage}
                      </div>
                    </div>
                    <div className="p-4 bg-[#0F1113] rounded-lg border border-emerald-900/40">
                      <div className="text-sm font-medium text-orange-300">SNAP Rate</div>
                      <div className="text-2xl font-bold text-orange-300">
                        {selectedZip.snap_rate != null ? `${(selectedZip.snap_rate * 100).toFixed(1)}%` : 'Loading...'}
                      </div>
                    </div>
                    <div className="p-4 bg-[#0F1113] rounded-lg border border-emerald-900/40">
                      <div className="text-sm font-medium text-slate-300">SNAP Stores</div>
                      <div className="text-2xl font-bold text-slate-100">
                        {selectedZip.snap_retailers != null ? selectedZip.snap_retailers : 'Loading...'}
                      </div>
                    </div>
                  </div>
                </div>
                
                {/* Additional Info */}
                <div className="mt-8 p-6 bg-[#0F1113] rounded-xl border border-emerald-900/40">
                  <h4 className="font-bold text-slate-100 mb-3 text-lg">What This Means</h4>
                  <p className="text-slate-300 leading-relaxed">
                    {selectedZip.affordability_score != null && selectedZip.affordability_score >= 15
                      ? `This area may face food affordability challenges. Healthy groceries represent ${selectedZip.affordability_score}% of local median income, which is above the ideal threshold.`
                      : selectedZip.affordability_score != null 
                      ? `This area has good food affordability. Healthy groceries represent only ${selectedZip.affordability_score}% of local median income.`
                      : 'Loading detailed analysis...'
                    }
                  </p>
                </div>

                {/* ML Risk Assessment */}
                {(() => {
                  const riskData = riskPredictions.find(r => r.zip_code === selectedZip.zip_code);
                  if (riskData) {
                    return (
                      <div className="mt-8 p-6 bg-[#0F1113] rounded-xl border border-emerald-900/40">
                        <h4 className="font-semibold text-slate-100 mb-4 text-lg">AI Risk Assessment</h4>
                        <div className="flex justify-between items-center">
                          <span className="font-medium">Risk Level:</span>
                          <span className={`px-3 py-1 rounded-full text-sm font-bold ${
                            riskData.risk_level.includes('High') ? 'bg-red-900/30 text-red-300 border border-red-900/50' :
                            riskData.risk_level.includes('Moderate') ? 'bg-amber-900/30 text-amber-300 border border-amber-900/50' :
                            'bg-emerald-900/30 text-emerald-300 border border-emerald-900/50'
                          }`}>
                            {riskData.risk_level}
                          </span>
                        </div>
                        <div className="mt-3">
                          <div className="text-sm text-slate-400">
                            Risk Probability: {(riskData.risk_probability * 100).toFixed(1)}%
                          </div>
                        </div>
                      </div>
                    );
                  }
                  return null;
                })()}
              </div>
            )}
          </div>
        )}

        {activeView === 'risk-prediction' && (
          <div className="space-y-6">
            {/* Explanation Header */}
            <div className="bg-[#101315] rounded-xl p-8 shadow-lg border border-emerald-900/30">
              <h2 className="text-3xl font-bold text-slate-100 mb-4">AI Risk Assessment</h2>
              <div className="bg-[#0F1113] border-l-4 border-emerald-700 p-6 rounded-r-lg mb-6">
                <div className="text-slate-300">
                  <p className="mb-2">
                    <strong>About the Food Affordability Score:</strong>
                  </p>
                  <p className="text-sm mb-2">
                    This score compares how expensive a basket of healthy groceries is relative to the median income in a ZIP code. 
                    It's calculated as: <code className="bg-[#131517] border border-emerald-900/40 text-slate-200 px-1 rounded">basket_cost ÷ median_income × 100</code>
                  </p>
                  <div className="grid md:grid-cols-2 gap-4 text-sm">
                    <div>
                      <p><strong>A lower score (under 1.5%)</strong> = groceries are very affordable</p>
                      <p className="text-xs text-slate-400 mt-2">Data: U.S. Census {dataVintage}</p>
                    </div>
                    <div>
                      <p><strong>A higher score (above 4.0%)</strong> = groceries are expensive for local incomes (food desert risk)</p>
                    </div>
                  </div>
                  <p className="text-sm mt-2">
                    Our AI model uses this score — along with factors like SNAP retailer access and income level — to flag ZIP codes that may be at risk for food insecurity or limited access to healthy food.
                  </p>
                </div>
              </div>
              
              <div className="grid md:grid-cols-3 gap-4 mb-6">
                <div className="text-center">
                  <div className="text-3xl font-bold text-emerald-400">{riskPredictions.length}</div>
                  <div className="text-sm text-slate-400">ZIP codes analyzed</div>
                </div>
                <div className="text-center">
                  <div className="text-3xl font-bold text-red-400">
                    {riskPredictions.filter(r => r.risk_prediction === 1).length}
                  </div>
                  <div className="text-sm text-slate-400">Flagged as "At Risk"</div>
                </div>
                <div className="text-center">
                  <div className="text-3xl font-bold text-orange-400">
                    {riskPredictions.filter(r => r.risk_level.includes('High')).length}
                  </div>
                  <div className="text-sm text-slate-400">High Risk Level</div>
                </div>
              </div>
            </div>

            {/* Search Interface */}
            <div className="bg-[#101315] rounded-xl p-8 shadow-lg border border-emerald-900/30">
              <h3 className="text-lg font-semibold text-slate-100 mb-4">Search ZIP Code Risk Assessment</h3>
              
              <div className="flex gap-4 mb-4">
                <div className="flex-1 relative">
                  <input
                    type="text"
                    placeholder="Search by ZIP code, city, or county to view ML risk assessment..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full px-6 py-4 text-lg bg-[#0F1113] text-slate-100 placeholder-slate-500 border-2 border-emerald-900/30 rounded-lg focus:border-emerald-500 focus:outline-none transition-colors"
                  />
                  
                  {/* Search Results Dropdown for ML Risk */}
                  {searchResults.length > 0 && activeView === 'risk-prediction' && (
                    <div className="absolute top-full left-0 right-0 bg-[#0F1113] text-slate-100 border border-emerald-900/30 rounded-lg mt-2 shadow-xl z-50 max-h-96 overflow-y-auto">
                      {searchResults.map((result) => {
                        const riskData = riskPredictions.find(r => r.zip_code === result.zip_code);
                        return (
                          <div
                            key={result.zip_code}
                            className="p-4 hover:bg-[#131517] cursor-pointer border-b border-emerald-900/20 last:border-b-0 transition-colors"
                            onClick={async () => {
                              // Fetch complete ZIP data for the selected ZIP
                              try {
                                const response = await fetch(`${BACKEND_URL}/api/affordability/${result.zip_code}`);
                                const completeZipData = await response.json();
                                const riskData = riskPredictions.find(r => r.zip_code === result.zip_code);
                                setSelectedZip({...completeZipData, riskData});
                                setSearchQuery('');
                                setSearchResults([]);
                              } catch (error) {
                                console.error('Error fetching complete ZIP data:', error);
                                // Fallback to basic data
                                const riskData = riskPredictions.find(r => r.zip_code === result.zip_code);
                                setSelectedZip({...result, riskData});
                                setSearchQuery('');
                                setSearchResults([]);
                              }
                            }}
                          >
                            <div className="flex justify-between items-center">
                              <div>
                                <span className="font-medium text-slate-100">{result.zip_code}</span>
                                <span className="text-slate-400 ml-2">{result.city}, {result.county} County</span>
                              </div>
                              <div className="flex items-center">
                                {riskData && (
                                  <span className={`px-3 py-1 rounded-full text-xs font-bold border ${
                                    riskData.risk_prediction === 1 ? 'bg-red-900/30 text-red-300 border-red-900/50' : 'bg-emerald-900/30 text-emerald-300 border-emerald-900/50'
                                  }`}>
                                    {riskData.risk_prediction === 1 ? 'At Risk' : 'Safe'}
                                  </span>
                                )}
                                <div
                                  className="w-3 h-3 rounded-full ml-2"
                                  style={{ backgroundColor: getColorByScore(result.affordability_score) }}
                                ></div>
                              </div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
                
                <button
                  onClick={() => setShowAtRiskOnly(!showAtRiskOnly)}
                  className={`px-6 py-3 rounded-lg font-semibold transition-colors border ${
                    showAtRiskOnly
                      ? 'bg-red-700 text-white border-red-600 hover:bg-red-600'
                      : 'bg-[#131517] text-slate-200 border-emerald-900/30 hover:border-emerald-700/50 hover:text-white'
                  }`}
                >
                  {showAtRiskOnly ? 'At-Risk Only' : 'Show All'}
                </button>
              </div>
              
              <p className="text-sm text-slate-400">
                Search for any ZIP code above to view detailed ML risk assessment, or browse the high-risk areas below.
              </p>
            </div>

            {/* Selected ZIP Risk Details */}
            {selectedZip && selectedZip.riskData && (
              <div className="bg-[#101315] rounded-xl p-8 shadow-lg border border-emerald-900/30">
                <h3 className="text-xl font-bold text-gray-900 mb-4">
                  ML Risk Assessment: ZIP {selectedZip.zip_code}
                </h3>
                <p className="text-slate-400 mb-4">{selectedZip.city}, {selectedZip.county} County</p>
                
                <div className="grid md:grid-cols-2 gap-6">
                  {/* Risk Overview */}
                  <div className="space-y-4">
                    <div className={`p-4 rounded-lg border-2 ${
                      selectedZip.riskData.risk_prediction === 1 ? 'bg-red-900/20 border-red-900/40' : 'bg-emerald-900/20 border-emerald-900/40'
                    }`}>
                      <div className="font-semibold text-lg mb-1">
                        {selectedZip.riskData.risk_prediction === 1 ? 'At Risk' : 'Safe'}
                      </div>
                      <div className="text-sm text-slate-300">ML Prediction</div>
                    </div>
                    
                    <div className="grid grid-cols-2 gap-3">
                      <div className="p-3 bg-[#0F1113] rounded-lg border border-emerald-900/30">
                        <div className="font-medium text-slate-100">Risk Level</div>
                        <div className={`text-sm font-bold ${
                          selectedZip.riskData.risk_level.includes('High') ? 'text-red-300' :
                          selectedZip.riskData.risk_level.includes('Moderate') ? 'text-amber-300' :
                          'text-emerald-300'
                        }`}>
                          {selectedZip.riskData.risk_level}
                        </div>
                      </div>
                      <div className="p-3 bg-[#0F1113] rounded-lg border border-emerald-900/30">
                        <div className="font-medium text-slate-100">Probability</div>
                        <div className="text-sm font-bold text-emerald-400">
                          {(selectedZip.riskData.risk_probability * 100).toFixed(1)}%
                        </div>
                      </div>
                    </div>
                  </div>
                  
                  {/* Affordability Details */}
                  <div className="space-y-4">
                    <div className="p-4 rounded-lg border-2" style={{ backgroundColor: `${getColorByScore(selectedZip.affordability_score)}20`, borderColor: `${getColorByScore(selectedZip.affordability_score)}40` }}>
                      <div className="font-semibold text-lg mb-1" style={{ color: getColorByScore(selectedZip.affordability_score) }}>
                        {selectedZip.affordability_score}% Affordability Score
                      </div>
                      <div className="text-sm text-slate-300">
                        {selectedZip.classification}
                      </div>
                    </div>
                    
                    <div className="grid grid-cols-2 gap-3 text-sm">
                      <div className="p-3 bg-[#0F1113] rounded-lg border border-emerald-900/30">
                        <div className="font-medium text-slate-100">Basket Cost</div>
                        <div className="text-sm font-bold text-emerald-400">
                          ${selectedZip.basket_cost != null ? selectedZip.basket_cost.toFixed(2) : 'Loading...'}
                        </div>
                      </div>
                      <div className="p-3 bg-[#0F1113] rounded-lg border border-emerald-900/30">
                        <div className="font-medium text-slate-100">Median Income</div>
                        <div className="text-sm font-bold text-emerald-400">
                          ${selectedZip.median_income != null ? (selectedZip.median_income / 1000).toFixed(0) : 'Loading...'}k
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
                
                <div className="mt-6 p-4 bg-[#0F1113] rounded-lg border border-emerald-900/40">
                  <h4 className="font-medium text-slate-100 mb-2">What This Means:</h4>
                  <p className="text-sm text-slate-300">
                    {selectedZip.riskData.risk_prediction === 1 
                      ? `This ZIP code is flagged as "At Risk" because the cost of healthy groceries represents ${selectedZip.affordability_score}% of local median income, which is above our threshold for food affordability concerns.`
                      : `This ZIP code is considered "Safe" because healthy groceries are relatively affordable at ${selectedZip.affordability_score}% of local median income.`
                    }
                  </p>
                </div>
              </div>
            )}

            {/* High Risk Areas Summary */}
            <div className="bg-[#101315] rounded-xl p-8 shadow-lg border border-emerald-900/30">
              <h3 className="text-lg font-semibold text-slate-100 mb-4">Areas Flagged as "At Risk" by AI Model</h3>
              
              {riskPredictions.filter(r => r.risk_prediction === 1).length > 0 ? (
                <div className="space-y-3">
                  {riskPredictions
                    .filter(r => r.risk_prediction === 1)
                    .sort((a, b) => b.risk_probability - a.risk_probability)
                    .slice(0, 10)
                    .map((prediction) => {
                      const zipData = affordabilityData.find(z => z.zip_code === prediction.zip_code);
                      return (
                        <div 
                          key={prediction.zip_code}
                          className="flex justify-between items-center p-4 bg-red-900/20 rounded-lg border border-red-900/40 hover:bg-red-900/30 cursor-pointer transition-colors"
                          onClick={() => setSelectedZip({...zipData, riskData: prediction})}
                        >
                          <div>
                            <span className="font-medium text-slate-100">{prediction.zip_code}</span>
                            <span className="text-slate-400 ml-2">
                              {zipData ? `${zipData.city}, ${zipData.county}` : 'Unknown'}
                            </span>
                          </div>
                          <div className="flex items-center">
                            <span className="text-sm text-red-300 mr-3">
                              {(prediction.risk_probability * 100).toFixed(1)}% risk
                            </span>
                            <span className="px-2 py-1 bg-red-900/30 text-red-300 border border-red-900/50 rounded text-xs font-bold">
                              {prediction.risk_level}
                            </span>
                          </div>
                        </div>
                      );
                    })}
                  
                  {riskPredictions.filter(r => r.risk_prediction === 1).length > 10 && (
                    <p className="text-sm text-slate-400 text-center mt-4">
                      Showing top 10 highest risk areas. Use search above to find specific ZIP codes.
                    </p>
                  )}
                </div>
              ) : (
                <div className="text-center py-8 text-slate-400">
                  <p className="text-lg font-medium">Great News!</p>
                  <p className="text-sm">No ZIP codes are currently flagged as "At Risk" by our AI model.</p>
                </div>
              )}
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="bg-[#101010] text-slate-100 border-t border-emerald-900/40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between">
            <div>
              <h3 className="text-lg font-semibold mb-2">Garden State Grocery Gap</h3>
              <p className="text-slate-400">
                Data-driven insights for food justice in New Jersey
              </p>
            </div>
            <div className="mt-4 md:mt-0">
              <p className="text-slate-400 text-sm">
                Built for policymakers, advocates, and communities
              </p>
              {dashboardStats && (
                <p className="text-slate-500 text-xs mt-1">
                  Analyzing {dashboardStats.total_zip_codes} ZIP codes • {
                    dashboardStats.using_real_demographics ?
                    'Real Census + SNAP demographic data' :
                    'Mock grocery pricing data'
                  }
                </p>
              )}
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;