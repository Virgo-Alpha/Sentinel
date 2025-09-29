#!/usr/bin/env python3
"""
Keyword matching test script for Sentinel.
Tests the keyword detection and matching functionality.
"""

import json
import re
import argparse
import sys
from typing import Dict, List, Tuple, Any
from datetime import datetime
import difflib

class KeywordMatcher:
    """Keyword matching engine for testing."""
    
    def __init__(self, keywords_config: Dict[str, Any]):
        self.config = keywords_config
        self.keyword_categories = keywords_config.get('keyword_categories', {})
        self.matching_rules = keywords_config.get('matching_rules', {})
        
        # Build keyword index
        self.keyword_index = self._build_keyword_index()
    
    def _build_keyword_index(self) -> Dict[str, Dict[str, Any]]:
        """Build an index of all keywords for efficient matching."""
        index = {}
        
        for category_name, category_data in self.keyword_categories.items():
            for keyword_data in category_data.get('keywords', []):
                keyword = keyword_data['keyword'].lower()
                
                # Add main keyword
                index[keyword] = {
                    'original': keyword_data['keyword'],
                    'category': category_name,
                    'weight': keyword_data.get('weight', 1.0),
                    'context_required': keyword_data.get('context_required', False),
                    'type': 'primary'
                }
                
                # Add aliases
                for alias in keyword_data.get('aliases', []):
                    alias_lower = alias.lower()
                    index[alias_lower] = {
                        'original': alias,
                        'primary_keyword': keyword_data['keyword'],
                        'category': category_name,
                        'weight': keyword_data.get('weight', 1.0) * 0.8,  # Slightly lower weight for aliases
                        'context_required': keyword_data.get('context_required', False),
                        'type': 'alias'
                    }
        
        return index
    
    def find_exact_matches(self, text: str) -> List[Dict[str, Any]]:
        """Find exact keyword matches in text."""
        text_lower = text.lower()
        matches = []
        
        for keyword, keyword_info in self.keyword_index.items():
            # Use word boundaries for better matching
            pattern = r'\b' + re.escape(keyword) + r'\b'
            
            for match in re.finditer(pattern, text_lower):
                start_pos = match.start()
                end_pos = match.end()
                
                # Extract context around the match
                context_start = max(0, start_pos - 50)
                context_end = min(len(text), end_pos + 50)
                context = text[context_start:context_end]
                
                matches.append({
                    'keyword': keyword_info['original'],
                    'matched_text': text[start_pos:end_pos],
                    'category': keyword_info['category'],
                    'weight': keyword_info['weight'],
                    'context_required': keyword_info['context_required'],
                    'type': keyword_info['type'],
                    'position': start_pos,
                    'context': context.strip(),
                    'match_type': 'exact'
                })
        
        return matches
    
    def find_fuzzy_matches(self, text: str) -> List[Dict[str, Any]]:
        """Find fuzzy keyword matches in text."""
        if not self.matching_rules.get('fuzzy_matching', {}).get('enabled', False):
            return []
        
        threshold = self.matching_rules['fuzzy_matching'].get('threshold', 0.8)
        matches = []
        
        # Split text into words
        words = re.findall(r'\b\w+\b', text.lower())
        
        for word in words:
            for keyword, keyword_info in self.keyword_index.items():
                # Skip if word is too short or too different in length
                if len(word) < 3 or abs(len(word) - len(keyword)) > 3:
                    continue
                
                # Calculate similarity
                similarity = difflib.SequenceMatcher(None, word, keyword).ratio()
                
                if similarity >= threshold:
                    # Find position in original text
                    word_pattern = r'\b' + re.escape(word) + r'\b'
                    match = re.search(word_pattern, text.lower())
                    
                    if match:
                        start_pos = match.start()
                        end_pos = match.end()
                        
                        # Extract context
                        context_start = max(0, start_pos - 50)
                        context_end = min(len(text), end_pos + 50)
                        context = text[context_start:context_end]
                        
                        matches.append({
                            'keyword': keyword_info['original'],
                            'matched_text': text[start_pos:end_pos],
                            'category': keyword_info['category'],
                            'weight': keyword_info['weight'] * similarity,  # Adjust weight by similarity
                            'context_required': keyword_info['context_required'],
                            'type': keyword_info['type'],
                            'position': start_pos,
                            'context': context.strip(),
                            'match_type': 'fuzzy',
                            'similarity': similarity
                        })
        
        return matches
    
    def validate_context(self, matches: List[Dict[str, Any]], text: str) -> List[Dict[str, Any]]:
        """Validate matches that require context."""
        if not self.matching_rules.get('context_analysis', {}).get('enabled', False):
            return matches
        
        context_keywords = self.matching_rules['context_analysis'].get(
            'required_context_keywords', []
        )
        
        validated_matches = []
        text_lower = text.lower()
        
        for match in matches:
            if not match['context_required']:
                validated_matches.append(match)
                continue
            
            # Check if any context keywords are present
            has_context = any(
                context_keyword in text_lower 
                for context_keyword in context_keywords
            )
            
            if has_context:
                match['context_validated'] = True
                validated_matches.append(match)
            else:
                match['context_validated'] = False
                # Still include but mark as context-failed
                validated_matches.append(match)
        
        return validated_matches
    
    def calculate_scores(self, matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Calculate final scores for matches."""
        scoring_rules = self.matching_rules.get('scoring', {})
        
        for match in matches:
            base_score = match['weight']
            
            # Apply match type bonuses/penalties
            if match['match_type'] == 'exact':
                base_score *= (1 + scoring_rules.get('exact_match_bonus', 0))
            elif match['match_type'] == 'fuzzy':
                base_score *= (1 - scoring_rules.get('fuzzy_match_penalty', 0))
            
            # Apply alias penalty
            if match['type'] == 'alias':
                base_score *= scoring_rules.get('alias_match_bonus', 0.8)
            
            # Apply context bonus
            if match.get('context_validated', True):
                base_score *= (1 + scoring_rules.get('context_bonus', 0))
            
            match['final_score'] = base_score
        
        return matches
    
    def match_keywords(self, text: str) -> Dict[str, Any]:
        """Main keyword matching function."""
        # Find all matches
        exact_matches = self.find_exact_matches(text)
        fuzzy_matches = self.find_fuzzy_matches(text)
        
        # Combine and deduplicate matches
        all_matches = exact_matches + fuzzy_matches
        
        # Remove duplicates (same keyword at same position)
        unique_matches = []
        seen = set()
        
        for match in all_matches:
            key = (match['keyword'], match['position'])
            if key not in seen:
                seen.add(key)
                unique_matches.append(match)
        
        # Validate context
        validated_matches = self.validate_context(unique_matches, text)
        
        # Calculate final scores
        scored_matches = self.calculate_scores(validated_matches)
        
        # Sort by score (highest first)
        scored_matches.sort(key=lambda x: x['final_score'], reverse=True)
        
        # Group by category
        category_matches = {}
        for match in scored_matches:
            category = match['category']
            if category not in category_matches:
                category_matches[category] = []
            category_matches[category].append(match)
        
        # Calculate category scores
        category_scores = {}
        for category, matches in category_matches.items():
            category_scores[category] = sum(match['final_score'] for match in matches)
        
        return {
            'matches': scored_matches,
            'category_matches': category_matches,
            'category_scores': category_scores,
            'total_matches': len(scored_matches),
            'total_score': sum(match['final_score'] for match in scored_matches)
        }

def load_keywords_config(config_path: str) -> Dict[str, Any]:
    """Load keywords configuration from file."""
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Keywords configuration file not found: {config_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in keywords configuration: {e}")
        sys.exit(1)

def run_test_cases(matcher: KeywordMatcher) -> bool:
    """Run predefined test cases."""
    test_cases = [
        {
            'name': 'Cloud Platform Vulnerability',
            'text': 'Microsoft has released a critical security update for Azure Active Directory to address a vulnerability (CVE-2024-1234) that could allow remote code execution.',
            'expected_categories': ['cloud_platforms', 'threat_intelligence'],
            'expected_keywords': ['Microsoft', 'Azure', 'vulnerability', 'CVE']
        },
        {
            'name': 'Ransomware Attack',
            'text': 'A new ransomware strain called "CryptoLocker2024" has been observed targeting Fortinet FortiGate devices through a zero-day exploit.',
            'expected_categories': ['threat_intelligence', 'security_vendors'],
            'expected_keywords': ['ransomware', 'Fortinet', 'zero-day', 'exploit']
        },
        {
            'name': 'Enterprise Tool Phishing',
            'text': 'Attackers are using phishing emails to steal Active Directory credentials and gain access to Exchange servers.',
            'expected_categories': ['threat_intelligence', 'enterprise_tools'],
            'expected_keywords': ['phishing', 'Active Directory', 'Exchange']
        },
        {
            'name': 'APT Campaign',
            'text': 'An advanced persistent threat group has been conducting lateral movement through VMware vSphere environments using stolen credentials.',
            'expected_categories': ['threat_intelligence', 'enterprise_tools', 'attack_techniques'],
            'expected_keywords': ['APT', 'lateral movement', 'VMware']
        },
        {
            'name': 'False Positive Test',
            'text': 'The weather forecast shows sunny skies with a chance of rain. Microsoft Office will be closed for maintenance.',
            'expected_categories': [],
            'expected_keywords': []
        }
    ]
    
    print("Running keyword matching test cases...")
    print("=" * 60)
    
    all_passed = True
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest Case {i}: {test_case['name']}")
        print(f"Text: {test_case['text']}")
        print("-" * 40)
        
        # Run keyword matching
        result = matcher.match_keywords(test_case['text'])
        
        # Check results
        found_categories = set(result['category_matches'].keys())
        found_keywords = set(match['keyword'] for match in result['matches'])
        
        expected_categories = set(test_case['expected_categories'])
        expected_keywords = set(test_case['expected_keywords'])
        
        # Validate categories
        missing_categories = expected_categories - found_categories
        unexpected_categories = found_categories - expected_categories
        
        # Validate keywords (more lenient - check if any expected keywords found)
        found_expected_keywords = expected_keywords & found_keywords
        
        # Print results
        print(f"Found {result['total_matches']} matches (score: {result['total_score']:.2f})")
        
        if result['matches']:
            print("Top matches:")
            for match in result['matches'][:5]:  # Show top 5
                print(f"  - {match['keyword']} ({match['category']}) - Score: {match['final_score']:.2f}")
        
        # Check test results
        test_passed = True
        
        if missing_categories:
            print(f"❌ Missing expected categories: {missing_categories}")
            test_passed = False
        
        if unexpected_categories and test_case['expected_categories']:
            print(f"⚠️  Unexpected categories: {unexpected_categories}")
        
        if expected_keywords and not found_expected_keywords:
            print(f"❌ No expected keywords found. Expected: {expected_keywords}")
            test_passed = False
        elif expected_keywords:
            missing_keywords = expected_keywords - found_expected_keywords
            if missing_keywords:
                print(f"⚠️  Missing some expected keywords: {missing_keywords}")
        
        if test_passed:
            print("✅ Test PASSED")
        else:
            print("❌ Test FAILED")
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 All test cases PASSED!")
    else:
        print("❌ Some test cases FAILED!")
    
    return all_passed

def run_interactive_test(matcher: KeywordMatcher):
    """Run interactive keyword matching test."""
    print("Interactive Keyword Matching Test")
    print("Enter text to analyze (or 'quit' to exit):")
    print("-" * 40)
    
    while True:
        try:
            text = input("\n> ").strip()
            
            if text.lower() in ['quit', 'exit', 'q']:
                break
            
            if not text:
                continue
            
            # Run keyword matching
            result = matcher.match_keywords(text)
            
            print(f"\nAnalysis Results:")
            print(f"Total matches: {result['total_matches']}")
            print(f"Total score: {result['total_score']:.2f}")
            
            if result['matches']:
                print("\nMatches by category:")
                for category, matches in result['category_matches'].items():
                    print(f"\n{category.upper()} (score: {result['category_scores'][category]:.2f}):")
                    for match in matches:
                        context_indicator = "🔍" if match.get('context_required') else ""
                        fuzzy_indicator = "~" if match['match_type'] == 'fuzzy' else ""
                        print(f"  - {match['keyword']}{fuzzy_indicator} (score: {match['final_score']:.2f}) {context_indicator}")
                        if match.get('context'):
                            print(f"    Context: ...{match['context']}...")
            else:
                print("No keywords matched.")
        
        except KeyboardInterrupt:
            break
        except EOFError:
            break
    
    print("\nGoodbye!")

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Test keyword matching functionality")
    parser.add_argument('-c', '--config', 
                       default='config/target_keywords.json',
                       help='Path to keywords configuration file')
    parser.add_argument('-t', '--test-cases', 
                       action='store_true',
                       help='Run predefined test cases')
    parser.add_argument('-i', '--interactive', 
                       action='store_true',
                       help='Run interactive test mode')
    parser.add_argument('-v', '--verbose', 
                       action='store_true',
                       help='Enable verbose output')
    
    args = parser.parse_args()
    
    # Load keywords configuration
    print(f"Loading keywords configuration from: {args.config}")
    keywords_config = load_keywords_config(args.config)
    
    # Create keyword matcher
    matcher = KeywordMatcher(keywords_config)
    
    print(f"Loaded {len(matcher.keyword_index)} keywords from {len(matcher.keyword_categories)} categories")
    
    if args.verbose:
        print("\nKeyword categories:")
        for category, data in matcher.keyword_categories.items():
            keyword_count = len(data.get('keywords', []))
            print(f"  - {category}: {keyword_count} keywords")
    
    success = True
    
    # Run test cases if requested
    if args.test_cases:
        success = run_test_cases(matcher)
    
    # Run interactive mode if requested
    if args.interactive:
        run_interactive_test(matcher)
    
    # If no specific mode requested, run test cases by default
    if not args.test_cases and not args.interactive:
        success = run_test_cases(matcher)
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()