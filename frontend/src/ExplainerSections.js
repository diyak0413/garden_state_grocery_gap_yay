import React from 'react';

const ExplainerSections = () => {
  return (
    <div className="space-y-8 text-slate-100">
      {/* What is Food Access? */}
      <div className="bg-[#101315] rounded-xl p-6 border border-emerald-900/30">
        <h2 className="text-2xl font-bold text-slate-100 mb-4">What is Food Access?</h2>
        <div className="prose prose-lg prose-invert">
          <p className="text-slate-300 mb-4">
            <strong>Food access</strong> means how easy and affordable it is for people to buy healthy, nutritious food in their neighborhood. 
            Think of it like this: Can a family easily walk or drive to a grocery store and afford to buy fresh fruits, vegetables, 
            and other healthy foods?
          </p>
          <div className="grid md:grid-cols-2 gap-6 mt-6">
            <div className="bg-[#0F1113] p-4 rounded-lg border border-emerald-900/40">
              <h3 className="font-semibold text-emerald-300 mb-2">Good Food Access</h3>
              <ul className="text-sm text-slate-300 space-y-1">
                <li>• Multiple grocery stores nearby</li>
                <li>• Fresh produce available</li>
                <li>• Prices families can afford</li>
                <li>• Easy to reach by car or walking</li>
              </ul>
            </div>
            <div className="bg-[#0F1113] p-4 rounded-lg border border-red-900/40">
              <h3 className="font-semibold text-red-300 mb-2">Poor Food Access</h3>
              <ul className="text-sm text-slate-300 space-y-1">
                <li>• Few or no grocery stores</li>
                <li>• Limited fresh, healthy options</li>
                <li>• Food is too expensive</li>
                <li>• Hard to reach without a car</li>
              </ul>
            </div>
          </div>
        </div>
      </div>

      {/* What is a Food Desert? */}
      <div className="bg-[#101315] rounded-xl p-6 border border-emerald-900/30">
        <h2 className="text-2xl font-bold text-slate-100 mb-4">What is a Food Desert?</h2>
        <div className="prose prose-lg prose-invert">
          <p className="text-slate-300 mb-4">
            A <strong>"food desert"</strong> is an area where people have limited access to affordable, nutritious food. 
            It's called a "desert" because healthy food is scarce, just like water in a real desert.
          </p>
          <div className="bg-[#0F1113] p-4 rounded-lg border border-orange-900/40 mb-4">
            <h3 className="font-semibold text-orange-300 mb-2">Food Deserts Often Have:</h3>
            <div className="grid md:grid-cols-2 gap-4 text-sm">
              <ul className="text-slate-300 space-y-1">
                <li>• No full-service grocery stores</li>
                <li>• Only fast food and convenience stores</li>
                <li>• Higher prices for healthy food</li>
              </ul>
              <ul className="text-slate-300 space-y-1">
                <li>• Long distances to reach fresh food</li>
                <li>• Limited public transportation</li>
                <li>• Lower household incomes</li>
              </ul>
            </div>
          </div>
          <p className="text-slate-300">
            <strong>Why it matters:</strong> When people can't easily buy healthy food, they may rely on processed, 
            less nutritious options. This can lead to health problems like diabetes and heart disease.
          </p>
        </div>
      </div>

      {/* What is SNAP? */}
      <div className="bg-[#101315] rounded-xl p-6 border border-emerald-900/30">
        <h2 className="text-2xl font-bold text-slate-100 mb-4">What is SNAP?</h2>
        <div className="prose prose-lg prose-invert">
          <p className="text-slate-300 mb-4">
            <strong>SNAP</strong> stands for "Supplemental Nutrition Assistance Program" (formerly known as "food stamps"). 
            It's a government program that helps low-income families buy food.
          </p>
          <div className="grid md:grid-cols-2 gap-6">
            <div className="bg-[#0F1113] p-4 rounded-lg border border-emerald-900/40">
              <h3 className="font-semibold text-emerald-300 mb-2">How SNAP Works</h3>
              <ul className="text-sm text-slate-300 space-y-1">
                <li>• Families get money on an EBT card</li>
                <li>• Card works like a debit card</li>
                <li>• Can buy most foods at approved stores</li>
                <li>• Amount depends on family size and income</li>
              </ul>
            </div>
            <div className="bg-[#0F1113] p-4 rounded-lg border border-emerald-900/40">
              <h3 className="font-semibold text-slate-300 mb-2">SNAP in Our Dashboard</h3>
              <ul className="text-sm text-slate-300 space-y-1">
                <li>• Shows % of people using SNAP in each area</li>
                <li>• Higher SNAP rate = more families need help</li>
                <li>• We track SNAP-authorized stores</li>
                <li>• Filter to see only SNAP-eligible foods</li>
              </ul>
            </div>
          </div>
        </div>
      </div>

      {/* Affordability Score Explained */}
      <div className="bg-[#101315] rounded-xl p-6 border border-emerald-900/30">
        <h2 className="text-2xl font-bold text-slate-100 mb-4">How We Calculate Affordability Scores</h2>
        <div className="prose prose-lg prose-invert">
          <p className="text-slate-300 mb-4">
            Our <strong>Affordability Score</strong> shows how expensive healthy groceries are compared to local income in each ZIP code. 
            We use a simple formula: <strong>basket_cost ÷ median_income × 100</strong>
          </p>
          <p className="text-slate-300 mb-4">
            <strong>Higher scores mean worse affordability</strong> - when groceries cost more relative to what people earn, 
            families may struggle to afford healthy food.
          </p>
          <div className="grid md:grid-cols-4 gap-4 mb-6">
            <div className="bg-[#0F1113] p-3 rounded-lg text-center border border-emerald-900/40">
              <div className="text-2xl font-bold text-emerald-400">&lt;1.5%</div>
              <div className="text-sm text-emerald-300">Excellent Access</div>
              <div className="text-xs text-slate-400">ACS 2019–2023</div>
            </div>
            <div className="bg-[#0F1113] p-3 rounded-lg text-center border border-emerald-900/40">
              <div className="text-2xl font-bold text-amber-300">1.5-3.0%</div>
              <div className="text-sm text-amber-300">Good Access</div>
              <div className="text-xs text-slate-400">ACS 2019–2023</div>
            </div>
            <div className="bg-[#0F1113] p-3 rounded-lg text-center border border-emerald-900/40">
              <div className="text-2xl font-bold text-orange-300">3.0-4.0%</div>
              <div className="text-sm text-orange-300">Moderate Access</div>
              <div className="text-xs text-slate-400">ACS 2019–2023</div>
            </div>
            <div className="bg-[#0F1113] p-3 rounded-lg text-center border border-emerald-900/40">
              <div className="text-2xl font-bold text-red-300">≥4.0%</div>
              <div className="text-sm text-red-300">Food Desert Risk</div>
              <div className="text-xs text-slate-400">ACS 2019–2023</div>
            </div>
          </div>
          <div className="bg-[#0F1113] p-4 rounded-lg border border-emerald-900/40">
            <h3 className="font-semibold text-slate-100 mb-2">Simple Formula:</h3>
            <div className="bg-[#131517] border border-emerald-900/40 p-3 rounded text-center mb-3">
              <code className="text-lg font-mono text-slate-200">basket_cost ÷ median_income × 100</code>
            </div>
            <div className="text-sm text-slate-300">
              <p><strong>Example:</strong> If healthy groceries cost $120/month and median income is $5,000/month:</p>
              <p>Score = $120 ÷ $5,000 × 100 = <strong>2.4%</strong> (very affordable)</p>
              <p className="mt-2">If the same groceries cost $120 but income is only $800/month:</p>
              <p>Score = $120 ÷ $800 × 100 = <strong>15%</strong> (low food access - harder to afford)</p>
            </div>
          </div>
        </div>
      </div>

      {/* Machine Learning Explained */}
      <div className="bg-[#101315] rounded-xl p-6 border border-emerald-900/30">
        <h2 className="text-2xl font-bold text-slate-100 mb-4">AI Predictions: What Areas Need Help?</h2>
        <div className="prose prose-lg prose-invert">
          <p className="text-slate-300 mb-4">
            Our <strong>AI (Artificial Intelligence)</strong> system is like a smart computer that looks at patterns in the data 
            to predict which areas might become food deserts or need extra help in the future.
          </p>
          <div className="grid md:grid-cols-2 gap-6 mb-4">
            <div className="bg-[#0F1113] p-4 rounded-lg border border-emerald-900/40">
              <h3 className="font-semibold text-slate-100 mb-2">How Our AI Works</h3>
              <ul className="text-sm text-slate-300 space-y-1">
                <li>• Analyzes data from all ZIP codes</li>
                <li>• Looks for patterns and connections</li>
                <li>• Predicts future food access problems</li>
                <li>• Updates predictions as data changes</li>
              </ul>
            </div>
            <div className="bg-[#0F1113] p-4 rounded-lg border border-emerald-900/40">
              <h3 className="font-semibold text-slate-100 mb-2">Risk Levels Explained</h3>
              <ul className="text-sm text-slate-300 space-y-1">
                <li>• <span className="text-red-300 font-medium">Very High Risk</span>: Needs immediate attention</li>
                <li>• <span className="text-orange-300 font-medium">High Risk</span>: Should be monitored closely</li>
                <li>• <span className="text-amber-300 font-medium">Moderate Risk</span>: Some concerns</li>
                <li>• <span className="text-emerald-300 font-medium">Low Risk</span>: Generally stable</li>
              </ul>
            </div>
          </div>
          <p className="text-slate-300">
            <strong>Why this helps:</strong> By predicting problems before they happen, communities and policymakers can 
            take action early - like attracting new grocery stores or starting food assistance programs.
          </p>
        </div>
      </div>

      {/* How to Use This Dashboard */}
      <div className="bg-[#101315] rounded-xl p-6 border border-emerald-900/30">
        <h2 className="text-2xl font-bold text-slate-100 mb-4">How to Use This Dashboard</h2>
        <div className="prose prose-lg prose-invert">
          <div className="grid md:grid-cols-2 gap-6">
            <div className="bg-[#0F1113] p-4 rounded-lg border border-emerald-900/40">
              <h3 className="font-semibold text-slate-100 mb-2">Interactive Map</h3>
              <ul className="text-sm text-slate-300 space-y-1">
                <li>• See color-coded regions</li>
                <li>• Click on any area for details</li>
                <li>• Search for specific ZIP codes</li>
                <li>• View affordability scores & trends</li>
                <li>• See ML risk assessments</li>
              </ul>
            </div>
            <div className="bg-[#0F1113] p-4 rounded-lg border border-emerald-900/40">
              <h3 className="font-semibold text-slate-100 mb-2">ZIP Risk Prediction</h3>
              <ul className="text-sm text-slate-300 space-y-1">
                <li>• Search for specific ZIP codes</li>
                <li>• View AI risk predictions</li>
                <li>• Understand risk factors</li>
                <li>• See high-risk areas</li>
                <li>• Get detailed assessments</li>
              </ul>
            </div>
          </div>
          <div className="bg-[#0F1113] p-4 rounded-lg border border-emerald-900/40 mt-6">
            <h3 className="font-semibold text-slate-100 mb-2">Pro Tips</h3>
            <ul className="text-sm text-slate-300 space-y-1">
              <li>• Use the SNAP filter to see food assistance data</li>
              <li>• Click "Update Prices" to get current grocery costs</li>
              <li>• Compare your ZIP code with neighboring areas</li>
              <li>• Share findings with local community groups</li>
            </ul>
          </div>
        </div>
      </div>

      {/* Who Can Use This */}
      <div className="bg-[#101315] rounded-xl p-6 border border-emerald-900/30">
        <h2 className="text-2xl font-bold text-slate-100 mb-4">Who Can Use This Tool?</h2>
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          <div className="bg-[#0F1113] p-4 rounded-lg border border-emerald-900/40">
            <h3 className="font-semibold text-slate-100 mb-2">Government Officials</h3>
            <p className="text-sm text-slate-300">
              City planners, health departments, and policymakers can identify areas needing grocery stores or food programs.
            </p>
          </div>
          <div className="bg-[#0F1113] p-4 rounded-lg border border-emerald-900/40">
            <h3 className="font-semibold text-slate-100 mb-2">Community Groups</h3>
            <p className="text-sm text-slate-300">
              Nonprofits and advocates can use this data to support funding requests and plan food assistance programs.
            </p>
          </div>
          <div className="bg-[#0F1113] p-4 rounded-lg border border-emerald-900/40">
            <h3 className="font-semibold text-slate-100 mb-2">Researchers</h3>
            <p className="text-sm text-slate-300">
              Students and academics can analyze food access patterns for studies and policy recommendations.
            </p>
          </div>
          <div className="bg-[#0F1113] p-4 rounded-lg border border-emerald-900/40">
            <h3 className="font-semibold text-slate-100 mb-2">Journalists</h3>
            <p className="text-sm text-slate-300">
              Reporters can find data-driven stories about food inequality and community health issues.
            </p>
          </div>
          <div className="bg-[#0F1113] p-4 rounded-lg border border-emerald-900/40">
            <h3 className="font-semibold text-slate-100 mb-2">Business Owners</h3>
            <p className="text-sm text-slate-300">
              Grocery chains and retailers can identify underserved markets for new store locations.
            </p>
          </div>
          <div className="bg-[#0F1113] p-4 rounded-lg border border-emerald-900/40">
            <h3 className="font-semibold text-slate-100 mb-2">Families</h3>
            <p className="text-sm text-slate-300">
              Parents and community members can understand food access in their neighborhoods and advocate for change.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ExplainerSections;