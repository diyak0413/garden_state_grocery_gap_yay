"""
Machine Learning Food Desert Risk Prediction Model
Predicts which ZIP codes are at risk of becoming or remaining food deserts
Based on economic indicators, accessibility metrics, and demographic data
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, accuracy_score
import joblib
from datetime import datetime
from typing import Dict, List, Tuple
import os

class FoodDesertPredictor:
    """Machine Learning model to predict food desert risk"""
    
    def __init__(self):
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            class_weight='balanced'  # Handle imbalanced classes
        )
        self.scaler = StandardScaler()
        self.feature_names = [
            'affordability_score',
            'median_income',
            'snap_rate',
            'population_density',
            'grocery_store_density',
            'snap_retailer_density',
            'cost_to_income_ratio',
            'basket_cost',
            'price_volatility',
            'urban_rural_score'
        ]
        self.is_trained = False
        self.model_path = '/app/backend/models/food_desert_model.joblib'
        self.scaler_path = '/app/backend/models/scaler.joblib'
        
        # Create models directory if it doesn't exist
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
    
    def create_features(self, zip_data: List[Dict]) -> pd.DataFrame:
        """Create feature matrix from ZIP code data"""
        features = []
        
        for zip_info in zip_data:
            # Calculate population density (people per sq mile, estimated)
            pop_density = zip_info['population'] / 10  # Rough approximation
            
            # Calculate store densities (stores per 10k people)
            grocery_density = (zip_info.get('grocery_stores', 1) / zip_info['population']) * 10000
            snap_density = (zip_info.get('snap_retailers', 1) / zip_info['population']) * 10000
            
            # Urban/rural score based on population density
            urban_rural = min(pop_density / 1000, 1.0)  # 0 = rural, 1 = urban
            
            # Calculate price volatility (mock for now, would use real price history)
            price_volatility = np.random.uniform(0.05, 0.25)  # 5-25% volatility
            
            feature_row = {
                'affordability_score': zip_info.get('affordability_score', 50),
                'median_income': zip_info['median_income'],
                'snap_rate': zip_info.get('snap_rate', 0.1),
                'population_density': pop_density,
                'grocery_store_density': grocery_density,
                'snap_retailer_density': snap_density,
                'cost_to_income_ratio': zip_info.get('cost_to_income_ratio', 0.15),
                'basket_cost': zip_info.get('basket_cost', 35.0),
                'price_volatility': price_volatility,
                'urban_rural_score': urban_rural
            }
            
            features.append(feature_row)
        
        return pd.DataFrame(features)
    
    def create_labels(self, zip_data: List[Dict]) -> np.array:
        """Create target labels based on food access classification
        
        Note: Higher affordability_score = worse affordability = at risk
        """
        labels = []
        
        for zip_info in zip_data:
            affordability_score = zip_info.get('affordability_score', 50)
            classification = zip_info.get('classification', 'Moderate Food Access')
            
            # Higher affordability score means worse affordability (at risk)
            # Adjusted threshold based on real NJ data: Score ≥3.5% is considered at risk  
            # This captures areas like Camden (4.3%), Newark (4.6%), Atlantic City (4.6%)
            if affordability_score >= 3.5 or classification in ['Food Desert Risk', 'Low Food Access']:
                labels.append(1)  # At risk
            else:
                labels.append(0)  # Not at risk
        
        return np.array(labels)
    
    def train_model(self, zip_data: List[Dict]) -> Dict:
        """Train the food desert prediction model"""
        print("🤖 Training Food Desert Risk Prediction Model...")
        
        # Create features and labels
        X = self.create_features(zip_data)
        y = self.create_labels(zip_data)
        
        print(f"📊 Training data: {len(X)} ZIP codes, {X.shape[1]} features")
        print(f"🏷️ Class distribution: {np.bincount(y)} (0=Safe, 1=At Risk)")
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Train model
        self.model.fit(X_train_scaled, y_train)
        
        # Evaluate model
        y_pred = self.model.predict(X_test_scaled)
        accuracy = accuracy_score(y_test, y_pred)
        
        # Get feature importance
        feature_importance = dict(zip(self.feature_names, self.model.feature_importances_))
        sorted_features = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)
        
        # Save model and scaler
        joblib.dump(self.model, self.model_path)
        joblib.dump(self.scaler, self.scaler_path)
        self.is_trained = True
        
        print(f"✅ Model trained successfully! Accuracy: {accuracy:.3f}")
        print("🎯 Top 5 most important features:")
        for feature, importance in sorted_features[:5]:
            print(f"   • {feature}: {importance:.3f}")
        
        return {
            'accuracy': accuracy,
            'feature_importance': dict(sorted_features),
            'training_samples': len(X_train),
            'test_samples': len(X_test),
            'model_saved': True
        }
    
    def load_model(self) -> bool:
        """Load trained model from disk"""
        try:
            if os.path.exists(self.model_path) and os.path.exists(self.scaler_path):
                self.model = joblib.load(self.model_path)
                self.scaler = joblib.load(self.scaler_path)
                self.is_trained = True
                print("✅ ML model loaded successfully")
                return True
            else:
                print("⚠️ No saved model found")
                return False
        except Exception as e:
            print(f"❌ Error loading model: {str(e)}")
            return False
    
    def predict_risk(self, zip_data: List[Dict]) -> List[Dict]:
        """Predict food desert risk for ZIP codes"""
        if not self.is_trained:
            if not self.load_model():
                raise ValueError("Model not trained or loaded")
        
        # Create features
        X = self.create_features(zip_data)
        X_scaled = self.scaler.transform(X)
        
        # Make predictions
        risk_predictions = self.model.predict(X_scaled)
        risk_probabilities = self.model.predict_proba(X_scaled)
        
        # Handle case where model only predicts one class
        if risk_probabilities.shape[1] == 1:
            # If only one class was predicted during training, create dummy probabilities
            single_class_probs = risk_probabilities[:, 0]
            risk_probabilities = np.column_stack([1 - single_class_probs, single_class_probs])
        
        # Create results
        results = []
        for i, zip_info in enumerate(zip_data):
            # Get the risk probability (probability of being "at risk" - class 1)
            if risk_probabilities.shape[1] > 1:
                # Normal case: model trained on both classes
                risk_prob = risk_probabilities[i][1]  # Probability of "at risk" class
                confidence = max(risk_probabilities[i])  # Highest class probability
            else:
                # Single class prediction case: model only learned one class during training
                # This happens when all training data belonged to one class
                # In this case, risk_predictions tells us what that single class was
                single_class_prob = risk_probabilities[i][0]  # The probability for the single class
                
                if len(set(self.model.classes_)) == 1:
                    # Model was trained on only one class
                    trained_class = self.model.classes_[0]
                    
                    if trained_class == 1:  # Model only learned "at risk" class
                        risk_prob = single_class_prob  # High probability = at risk
                        confidence = single_class_prob
                    else:  # Model only learned "safe" class (trained_class == 0)
                        risk_prob = 1 - single_class_prob  # Low probability = safe, so risk_prob should be low
                        confidence = single_class_prob
                else:
                    # Fallback: use the actual prediction to determine risk probability
                    if risk_predictions[i] == 1:  # Predicted as at-risk
                        risk_prob = single_class_prob
                        confidence = single_class_prob
                    else:  # Predicted as safe
                        risk_prob = 1 - single_class_prob
                        confidence = single_class_prob
            
            risk_level = self.get_risk_level(risk_prob)
            
            result = {
                'zip_code': zip_info.get('zip_code', zip_info.get('zip')),
                'city': zip_info.get('city', 'Unknown'),  # Include city information
                'county': zip_info.get('county', 'Unknown'),  # Include county information
                'risk_prediction': int(risk_predictions[i]),
                'risk_probability': round(risk_prob, 3),
                'risk_level': risk_level,
                'confidence': round(confidence, 3),
                'predicted_at': datetime.utcnow().isoformat()
            }
            results.append(result)
        
        return results
    
    def get_risk_level(self, risk_probability: float) -> str:
        """Convert risk probability to human-readable level"""
        if risk_probability >= 0.8:
            return "Very High Risk"
        elif risk_probability >= 0.6:
            return "High Risk"
        elif risk_probability >= 0.4:
            return "Moderate Risk"
        elif risk_probability >= 0.2:
            return "Low Risk"
        else:
            return "Very Low Risk"
    
    def get_feature_importance(self) -> Dict:
        """Get feature importance from trained model"""
        if not self.is_trained:
            return {}
        
        importance = dict(zip(self.feature_names, self.model.feature_importances_))
        return dict(sorted(importance.items(), key=lambda x: x[1], reverse=True))
    
    def explain_prediction(self, zip_code: str, zip_data: Dict) -> Dict:
        """Provide detailed explanation for a specific prediction"""
        if not self.is_trained:
            if not self.load_model():
                raise ValueError("Model not trained")
        
        # Get prediction for this ZIP code
        predictions = self.predict_risk([zip_data])
        prediction = predictions[0]
        
        # Get feature values
        features_df = self.create_features([zip_data])
        feature_values = features_df.iloc[0].to_dict()
        
        # Get feature importance
        importance = self.get_feature_importance()
        
        # Create explanation
        explanation = {
            'zip_code': zip_code,
            'prediction': prediction,
            'key_factors': [],
            'protective_factors': [],
            'improvement_suggestions': []
        }
        
        # Analyze key risk and protective factors
        for feature, value in feature_values.items():
            if feature in importance:
                factor_info = {
                    'factor': feature,
                    'value': round(value, 2),
                    'importance': round(importance[feature], 3)
                }
                
                # Determine if this is a risk or protective factor
                if self._is_risk_factor(feature, value):
                    explanation['key_factors'].append(factor_info)
                else:
                    explanation['protective_factors'].append(factor_info)
        
        # Sort by importance
        explanation['key_factors'].sort(key=lambda x: x['importance'], reverse=True)
        explanation['protective_factors'].sort(key=lambda x: x['importance'], reverse=True)
        
        # Generate improvement suggestions
        explanation['improvement_suggestions'] = self._generate_suggestions(feature_values)
        
        return explanation
    
    def _is_risk_factor(self, feature: str, value: float) -> bool:
        """Determine if a feature value represents a risk factor
        
        Note: For affordability_score, HIGHER values indicate MORE risk
        """
        risk_thresholds = {
            'affordability_score': 15,  # Higher = more risk (15+ is at risk, adjusted from 60)
            'median_income': 50000,     # Lower = more risk
            'snap_rate': 0.15,          # Higher = more risk
            'grocery_store_density': 2, # Lower = more risk
            'snap_retailer_density': 1, # Lower = more risk
            'cost_to_income_ratio': 0.15 # Higher = more risk
        }
        
        if feature in risk_thresholds:
            threshold = risk_thresholds[feature]
            if feature in ['affordability_score', 'snap_rate', 'cost_to_income_ratio']:
                return value > threshold  # Higher is worse for these metrics
            else:
                return value < threshold  # Lower is worse for income and store density
        
        return False
    
    def _generate_suggestions(self, features: Dict) -> List[str]:
        """Generate improvement suggestions based on feature values"""
        suggestions = []
        
        if features['affordability_score'] > 15:
            suggestions.append("Improve food affordability through subsidies or price controls")
        
        if features['grocery_store_density'] < 2:
            suggestions.append("Increase grocery store density through zoning incentives")
        
        if features['snap_retailer_density'] < 1:
            suggestions.append("Recruit more SNAP-authorized retailers in the area")
        
        if features['cost_to_income_ratio'] > 0.2:
            suggestions.append("Address income inequality or provide targeted food assistance")
        
        if features['snap_rate'] > 0.2:
            suggestions.append("Implement economic development programs to improve local incomes")
        
        return suggestions

# Global model instance
food_desert_predictor = FoodDesertPredictor()

def train_ml_model(zip_data: List[Dict]) -> Dict:
    """Train the ML model with ZIP code data"""
    return food_desert_predictor.train_model(zip_data)

def predict_food_desert_risk(zip_data: List[Dict]) -> List[Dict]:
    """Predict food desert risk for ZIP codes"""
    return food_desert_predictor.predict_risk(zip_data)

def explain_zip_prediction(zip_code: str, zip_data: Dict) -> Dict:
    """Get detailed explanation for a ZIP code prediction"""
    return food_desert_predictor.explain_prediction(zip_code, zip_data)

def get_model_info() -> Dict:
    """Get information about the ML model"""
    return {
        'model_type': 'Random Forest Classifier',
        'features': food_desert_predictor.feature_names,
        'is_trained': food_desert_predictor.is_trained,
        'feature_importance': food_desert_predictor.get_feature_importance() if food_desert_predictor.is_trained else {}
    }