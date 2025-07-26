import json
import google.generativeai as genai
from typing import List, Dict, Tuple, Optional
from datetime import datetime
from sqlalchemy import and_, or_
from src.models.database import get_database_session, User, LoanProduct, UserLoanMatch, ProcessingLog
import os
import time

class LoanMatchingEngine:
    def __init__(self):
        # Initialize Gemini AI
        genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
        self.model = genai.GenerativeModel('gemini-pro')
        
        # Matching thresholds and weights
        self.match_weights = {
            'credit_score': 0.35,
            'income': 0.25,
            'employment': 0.20,
            'age': 0.10,
            'loan_amount': 0.10
        }
        
        # Pre-filtering thresholds
        self.strict_filters = {
            'credit_score_buffer': 50,  # Allow 50 points below minimum
            'income_buffer_percent': 0.15,  # Allow 15% below minimum income
            'age_buffer': 2  # Allow 2 years outside age range
        }
    
    def run_matching_pipeline(self, batch_size: int = 100) -> Dict:
        """
        Main matching pipeline with multi-stage optimization
        """
        session = get_database_session()
        
        # Log start of matching process
        log_entry = ProcessingLog(
            process_type='matching',
            status='started',
            details='Starting user-loan matching pipeline'
        )
        session.add(log_entry)
        session.commit()
        
        try:
            # Stage 1: Get unprocessed users
            unprocessed_users = session.query(User).filter_by(processed=False).all()
            
            if not unprocessed_users:
                log_entry.status = 'completed'
                log_entry.details = 'No unprocessed users found'
                log_entry.completed_at = datetime.utcnow()
                session.commit()
                return {'success': True, 'matches_created': 0, 'users_processed': 0}
            
            # Stage 2: Get all active loan products
            loan_products = session.query(LoanProduct).filter_by(is_active=True).all()
            
            if not loan_products:
                raise Exception("No active loan products found")
            
            total_matches = 0
            users_processed = 0
            
            # Process users in batches
            for i in range(0, len(unprocessed_users), batch_size):
                batch_users = unprocessed_users[i:i + batch_size]
                
                batch_matches = self._process_user_batch(batch_users, loan_products, session)
                total_matches += batch_matches
                users_processed += len(batch_users)
                
                # Mark users as processed
                for user in batch_users:
                    user.processed = True
                
                session.commit()
                
                print(f"Processed batch {i//batch_size + 1}: {len(batch_users)} users, {batch_matches} matches")
            
            # Update log with success
            log_entry.status = 'completed'
            log_entry.records_processed = users_processed
            log_entry.completed_at = datetime.utcnow()
            log_entry.details = f'Successfully processed {users_processed} users, created {total_matches} matches'
            session.commit()
            
            return {
                'success': True,
                'users_processed': users_processed,
                'matches_created': total_matches
            }
            
        except Exception as e:
            # Update log with error
            log_entry.status = 'failed'
            log_entry.completed_at = datetime.utcnow()
            log_entry.details = f'Error during matching: {str(e)}'
            session.commit()
            raise
        finally:
            session.close()
    
    def _process_user_batch(self, users: List[User], loan_products: List[LoanProduct], session) -> int:
        """
        Process a batch of users through the multi-stage matching pipeline
        """
        total_matches = 0
        
        for user in users:
            try:
                # Stage 1: SQL-based pre-filtering (fast elimination)
                candidate_products = self._sql_prefilter(user, loan_products)
                
                if not candidate_products:
                    continue
                
                # Stage 2: Rule-based scoring (medium complexity)
                scored_products = self._rule_based_scoring(user, candidate_products)
                
                # Stage 3: AI-enhanced evaluation (for top candidates only)
                final_matches = self._ai_enhanced_evaluation(user, scored_products[:5], session)
                
                total_matches += len(final_matches)
                
            except Exception as e:
                print(f"Error processing user {user.user_id}: {e}")
                continue
        
        return total_matches
    
    def _sql_prefilter(self, user: User, loan_products: List[LoanProduct]) -> List[LoanProduct]:
        """
        Stage 1: Fast SQL-based pre-filtering to eliminate obviously incompatible products
        """
        candidates = []
        
        for product in loan_products:
            # Credit score check with buffer
            if product.min_credit_score:
                if user.credit_score < (product.min_credit_score - self.strict_filters['credit_score_buffer']):
                    continue
            
            if product.max_credit_score:
                if user.credit_score > product.max_credit_score:
                    continue
            
            # Income check with buffer
            if product.min_income_required:
                min_income_with_buffer = product.min_income_required * (1 - self.strict_filters['income_buffer_percent'])
                if user.monthly_income * 12 < min_income_with_buffer:
                    continue
            
            # Age check with buffer
            if product.age_min:
                if user.age < (product.age_min - self.strict_filters['age_buffer']):
                    continue
            
            if product.age_max:
                if user.age > (product.age_max + self.strict_filters['age_buffer']):
                    continue
            
            # Employment status basic check
            if product.employment_requirements:
                if not self._basic_employment_check(user.employment_status, product.employment_requirements):
                    continue
            
            candidates.append(product)
        
        return candidates
    
    def _basic_employment_check(self, user_employment: str, requirements: str) -> bool:
        """Basic employment status compatibility check"""
        user_emp_lower = user_employment.lower()
        req_lower = requirements.lower()
        
        # Simple keyword matching
        if 'unemployed' in user_emp_lower and 'employment' in req_lower:
            return False
        
        if 'student' in user_emp_lower and 'steady' in req_lower:
            return False
        
        return True
    
    def _rule_based_scoring(self, user: User, products: List[LoanProduct]) -> List[Tuple[LoanProduct, float]]:
        """
        Stage 2: Rule-based scoring system for medium complexity evaluation
        """
        scored_products = []
        
        for product in products:
            score = 0.0
            
            # Credit score scoring (35% weight)
            if product.min_credit_score and product.max_credit_score:
                credit_range = product.max_credit_score - product.min_credit_score
                if credit_range > 0:
                    credit_position = (user.credit_score - product.min_credit_score) / credit_range
                    credit_score = min(1.0, max(0.0, credit_position))
                else:
                    credit_score = 1.0 if user.credit_score >= product.min_credit_score else 0.0
            else:
                credit_score = 0.8  # Default score if no range specified
            
            score += credit_score * self.match_weights['credit_score']
            
            # Income scoring (25% weight)
            annual_income = user.monthly_income * 12
            if product.min_income_required:
                income_ratio = annual_income / product.min_income_required
                income_score = min(1.0, income_ratio)
            else:
                income_score = 0.8
            
            score += income_score * self.match_weights['income']
            
            # Employment scoring (20% weight)
            employment_score = self._score_employment_match(user.employment_status, product.employment_requirements)
            score += employment_score * self.match_weights['employment']
            
            # Age scoring (10% weight)
            age_score = self._score_age_match(user.age, product.age_min, product.age_max)
            score += age_score * self.match_weights['age']
            
            # Interest rate preference (10% weight) - lower is better
            if product.interest_rate_min:
                # Normalize interest rate (assuming 5-35% range)
                rate_score = max(0.0, (35 - product.interest_rate_min) / 30)
            else:
                rate_score = 0.5
            
            score += rate_score * self.match_weights['loan_amount']
            
            scored_products.append((product, score))
        
        # Sort by score descending
        scored_products.sort(key=lambda x: x[1], reverse=True)
        
        return scored_products
    
    def _score_employment_match(self, user_employment: str, requirements: str) -> float:
        """Score employment compatibility"""
        if not requirements:
            return 0.8
        
        user_emp_lower = user_employment.lower()
        req_lower = requirements.lower()
        
        # High compatibility scenarios
        if 'full-time' in user_emp_lower and ('steady' in req_lower or 'stable' in req_lower):
            return 1.0
        
        if 'employed' in user_emp_lower and 'employment' in req_lower:
            return 0.9
        
        if 'self-employed' in user_emp_lower and 'income' in req_lower:
            return 0.7
        
        if 'part-time' in user_emp_lower:
            return 0.6
        
        if 'unemployed' in user_emp_lower:
            return 0.1
        
        return 0.5  # Default for unclear cases
    
    def _score_age_match(self, user_age: int, min_age: Optional[int], max_age: Optional[int]) -> float:
        """Score age compatibility"""
        if not min_age and not max_age:
            return 1.0
        
        if min_age and user_age < min_age:
            return max(0.0, 1.0 - (min_age - user_age) * 0.1)
        
        if max_age and user_age > max_age:
            return max(0.0, 1.0 - (user_age - max_age) * 0.1)
        
        return 1.0
    
    def _ai_enhanced_evaluation(self, user: User, scored_products: List[Tuple[LoanProduct, float]], session) -> List[UserLoanMatch]:
        """
        Stage 3: AI-enhanced evaluation for top candidates using Gemini
        """
        matches = []
        
        if not scored_products:
            return matches
        
        try:
            # Prepare user profile for AI
            user_profile = {
                'credit_score': user.credit_score,
                'monthly_income': user.monthly_income,
                'annual_income': user.monthly_income * 12,
                'employment_status': user.employment_status,
                'age': user.age
            }
            
            # Process top candidates with AI
            for product, base_score in scored_products:
                try:
                    ai_evaluation = self._get_ai_match_evaluation(user_profile, product)
                    
                    if ai_evaluation['eligible']:
                        # Combine base score with AI confidence
                        final_score = (base_score * 0.7) + (ai_evaluation['confidence'] * 0.3)
                        
                        # Create match record
                        match = UserLoanMatch(
                            user_id=user.id,
                            loan_product_id=product.id,
                            match_score=final_score,
                            eligibility_status=ai_evaluation['status'],
                            match_reasons=json.dumps(ai_evaluation['reasons'])
                        )
                        
                        session.add(match)
                        matches.append(match)
                    
                    # Rate limiting for AI calls
                    time.sleep(0.5)
                    
                except Exception as e:
                    print(f"AI evaluation error for product {product.id}: {e}")
                    
                    # Fallback to rule-based decision
                    if base_score > 0.6:
                        match = UserLoanMatch(
                            user_id=user.id,
                            loan_product_id=product.id,
                            match_score=base_score,
                            eligibility_status='likely_eligible',
                            match_reasons=json.dumps(['Rule-based match', f'Score: {base_score:.2f}'])
                        )
                        
                        session.add(match)
                        matches.append(match)
        
        except Exception as e:
            print(f"AI evaluation batch error: {e}")
        
        return matches
    
    def _get_ai_match_evaluation(self, user_profile: Dict, product: LoanProduct) -> Dict:
        """
        Use Gemini AI to evaluate user-product compatibility
        """
        try:
            prompt = f"""
            Evaluate if this user is eligible for the given loan product. Provide a detailed analysis.

            User Profile:
            - Credit Score: {user_profile['credit_score']}
            - Annual Income: ${user_profile['annual_income']:,.2f}
            - Employment: {user_profile['employment_status']}
            - Age: {user_profile['age']}

            Loan Product:
            - Product: {product.product_name}
            - Lender: {product.lender_name}
            - Interest Rate: {product.interest_rate_min}% - {product.interest_rate_max}%
            - Loan Amount: ${product.min_loan_amount:,.0f} - ${product.max_loan_amount:,.0f}
            - Min Credit Score: {product.min_credit_score}
            - Min Income Required: ${product.min_income_required:,.0f}
            - Employment Requirements: {product.employment_requirements}
            - Age Range: {product.age_min} - {product.age_max}

            Respond in JSON format:
            {{
                "eligible": true/false,
                "confidence": 0.0-1.0,
                "status": "eligible"/"likely_eligible"/"needs_review",
                "reasons": ["reason1", "reason2", ...],
                "risk_factors": ["factor1", "factor2", ...] (if any)
            }}
            """
            
            response = self.model.generate_content(prompt)
            
            # Parse AI response
            try:
                ai_result = json.loads(response.text.strip())
                
                # Validate response structure
                required_keys = ['eligible', 'confidence', 'status', 'reasons']
                if all(key in ai_result for key in required_keys):
                    return ai_result
                else:
                    raise ValueError("Invalid AI response structure")
                    
            except json.JSONDecodeError:
                # Fallback parsing if JSON is malformed
                text = response.text.lower()
                
                if 'eligible' in text and 'true' in text:
                    return {
                        'eligible': True,
                        'confidence': 0.7,
                        'status': 'likely_eligible',
                        'reasons': ['AI analysis suggests eligibility']
                    }
                else:
                    return {
                        'eligible': False,
                        'confidence': 0.3,
                        'status': 'needs_review',
                        'reasons': ['AI analysis suggests review needed']
                    }
        
        except Exception as e:
            print(f"AI evaluation error: {e}")
            # Return conservative fallback
            return {
                'eligible': False,
                'confidence': 0.5,
                'status': 'needs_review',
                'reasons': [f'AI evaluation failed: {str(e)}']
            }

def run_user_loan_matching():
    """
    Main function to run the user-loan matching process
    """
    try:
        matcher = LoanMatchingEngine()
        result = matcher.run_matching_pipeline()
        
        print(f"Matching completed successfully:")
        print(f"- Users processed: {result['users_processed']}")
        print(f"- Matches created: {result['matches_created']}")
        
        return result
        
    except Exception as e:
        print(f"Error in matching process: {e}")
        return {'success': False, 'error': str(e)}

if __name__ == '__main__':
    result = run_user_loan_matching()
    print(json.dumps(result, indent=2))
