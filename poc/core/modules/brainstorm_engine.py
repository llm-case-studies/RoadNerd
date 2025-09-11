"""
RoadNerd Brainstorm Engine - High-creativity diagnostic idea generation and ranking

This module contains the core brainstorming and judging logic for generating
multiple structured diagnostic ideas from user issues, with sophisticated
JSON parsing strategies and deterministic ranking.
"""

import json
import uuid
import os
import re
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from .system_diagnostics import SystemDiagnostics
from .llm_interface import LLMInterface


class Idea:
    """Structured representation of a diagnostic/fix idea."""
    def __init__(self, hypothesis: str, category: str, why: str, 
                 checks: List[str] = None, fixes: List[str] = None, 
                 risk: str = "low", confidence: float = 0.5):
        self.id = str(uuid.uuid4())[:8]
        self.hypothesis = hypothesis
        self.category = category  # wifi, dns, network, performance, etc.
        self.why = why
        self.checks = checks or []
        self.fixes = fixes or []
        self.risk = risk  # low, medium, high
        self.confidence = confidence
        self.evidence = {}  # Will hold probe results
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'hypothesis': self.hypothesis,
            'category': self.category,
            'why': self.why,
            'checks': self.checks,
            'fixes': self.fixes,
            'risk': self.risk,
            'confidence': self.confidence,
            'evidence': self.evidence
        }


class TemplateLoader:
    """Handles template loading and rendering with mustache-like syntax."""
    
    @staticmethod
    def load_template(kind: str, category_hint: Optional[str] = None) -> str:
        """Load template with category-specific fallback."""
        base_dir = os.getenv('RN_PROMPT_DIR')
        search_dirs = []
        if base_dir:
            search_dirs.append(Path(base_dir))
        search_dirs.append(Path(__file__).parent.parent / 'prompts')

        names = []
        if category_hint:
            names.append(f"{kind}.{category_hint}.txt")
        names.append(f"{kind}.base.txt")

        for d in search_dirs:
            for name in names:
                p = d / name
                if p.exists():
                    try:
                        return p.read_text(encoding='utf-8')
                    except Exception:
                        continue
        # Fallback minimal template
        return "Issue: {{ISSUE}}\nSystem: {{SYSTEM}}\nChecks and fixes please."

    @staticmethod
    def render_template(tpl: str, ctx: Dict[str, str]) -> str:
        """Render template with mustache-like conditional blocks and replacements."""
        def toggle_block(text: str, key: str, value: str) -> str:
            start = f"{{{{#{key}}}}}"
            end = f"{{{{/{key}}}}}"
            while True:
                i = text.find(start)
                if i == -1:
                    break
                j = text.find(end, i)
                if j == -1:
                    break
                inner = text[i + len(start): j]
                replacement = inner if value else ''
                text = text[:i] + replacement + text[j + len(end):]
            return text

        out = tpl
        # Optional blocks
        out = toggle_block(out, 'CATEGORY_HINT', ctx.get('CATEGORY_HINT') or '')
        out = toggle_block(out, 'RETRIEVAL', ctx.get('RETRIEVAL') or '')
        # Simple replacements
        for k, v in ctx.items():
            out = out.replace(f"{{{{{k}}}}}", v or '')
        return out


class BrainstormEngine:
    """Generate multiple structured ideas for a given issue."""
    
    def __init__(self, llm_interface: LLMInterface):
        """Initialize with LLM interface dependency."""
        self.llm_interface = llm_interface
    
    def generate_ideas(self, issue: str, n: int = 5, creativity: int = 1, 
                      category_hint: Optional[str] = None, retrieval_text: str = "") -> List[Idea]:
        """Generate N ideas with specified creativity level (0-3)."""
        
        # Adjust LLM parameters based on creativity
        temperature_map = {0: 0.0, 1: 0.3, 2: 0.7, 3: 1.0}
        temperature = temperature_map.get(creativity, 0.3)
        
        # Build brainstorming prompt (template, optional category hint)
        system_info = SystemDiagnostics.get_system_info()
        connectivity = SystemDiagnostics.check_connectivity()
        tpl = TemplateLoader.load_template('brainstorm', category_hint=category_hint)
        ctx = {
            'SYSTEM': json.dumps(system_info, ensure_ascii=False),
            'CONNECTIVITY': json.dumps(connectivity, ensure_ascii=False),
            'ISSUE': issue,
            'CATEGORY_HINT': category_hint or '',
            'N': str(n),
            'RETRIEVAL': retrieval_text or '',
        }
        prompt = TemplateLoader.render_template(tpl, ctx)

        # Get LLM response with per-request creativity
        # Each JSON idea ~100-200 tokens, so scale appropriately
        num_predict = max(512, n * 120)  # At least 120 tokens per idea
        llm_response = self.llm_interface.get_response(
            prompt,
            temperature=temperature,
            num_predict=num_predict,
        )
        ideas = self._parse_ideas_response(llm_response, issue)
        
        return ideas[:n]  # Ensure we return exactly n ideas
    
    @staticmethod
    def _parse_ideas_response(response: str, issue: str) -> List[Idea]:
        """Parse LLM response into structured Idea objects (tolerant of arrays, fences)."""
        def to_idea(obj: Dict) -> Idea:
            return Idea(
                hypothesis=obj.get('hypothesis', 'Unknown hypothesis'),
                category=obj.get('category', 'general'),
                why=obj.get('why', 'No reasoning provided'),
                checks=obj.get('checks', []),
                fixes=obj.get('fixes', []),
                risk=obj.get('risk', 'medium')
            )

        ideas: List[Idea] = []

        text = response or ''

        # 1) Direct JSON parse (array or object)
        try:
            data = json.loads(text)
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        ideas.append(to_idea(item))
            elif isinstance(data, dict):
                # Possibly {"ideas": [...]}
                if isinstance(data.get('ideas'), list):
                    for item in data['ideas']:
                        if isinstance(item, dict):
                            ideas.append(to_idea(item))
                else:
                    ideas.append(to_idea(data))
        except Exception:
            pass

        # 2) Parse fenced code blocks ```json ... ```
        if not ideas:
            fence_pattern = re.compile(r"```(?:json)?\n(.*?)```", re.DOTALL | re.IGNORECASE)
            for block in fence_pattern.findall(text):
                block = block.strip()
                try:
                    blk = json.loads(block)
                    if isinstance(blk, list):
                        for item in blk:
                            if isinstance(item, dict):
                                ideas.append(to_idea(item))
                    elif isinstance(blk, dict):
                        if isinstance(blk.get('ideas'), list):
                            for item in blk['ideas']:
                                if isinstance(item, dict):
                                    ideas.append(to_idea(item))
                        else:
                            ideas.append(to_idea(blk))
                except Exception:
                    continue

        # 3) Parse numbered JSON list format (1. {...}, 2. {...})
        if not ideas:
            # Match numbered items with JSON objects
            numbered_pattern = re.compile(r'^\d+\.\s*(\{.*?\})', re.MULTILINE | re.DOTALL)
            for match in numbered_pattern.findall(text):
                try:
                    obj = json.loads(match)
                    if isinstance(obj, dict):
                        ideas.append(to_idea(obj))
                except Exception:
                    continue

        # 4) Curly-brace balanced objects found in text
        if not ideas:
            buf = []
            depth = 0
            for ch in text:
                if ch == '{':
                    depth += 1
                if depth > 0:
                    buf.append(ch)
                if ch == '}':
                    depth -= 1
                    if depth == 0 and buf:
                        candidate = ''.join(buf)
                        buf = []
                        try:
                            obj = json.loads(candidate)
                            if isinstance(obj, dict):
                                ideas.append(to_idea(obj))
                        except Exception:
                            continue

        # 5) Fallback
        if not ideas:
            ideas.append(Idea(
                hypothesis="Generic troubleshooting approach",
                category="general",
                why="LLM response could not be parsed into structured ideas",
                checks=["echo 'Manual analysis required'"],
                fixes=["Analyze the issue manually"],
                risk="low"
            ))

        return ideas


class JudgeEngine:
    """Score and rank ideas using deterministic criteria."""
    
    @staticmethod
    def judge_ideas(ideas: List[Idea], issue: str) -> List[Dict]:
        """Score and rank ideas, return ordered list with rationale."""
        
        scored_ideas = []
        system_info = SystemDiagnostics.get_system_info()
        
        for idea in ideas:
            scores = JudgeEngine._score_idea(idea, issue, system_info)
            
            # Calculate weighted total score
            total_score = (
                scores['safety'] * 0.3 +
                scores['success_likelihood'] * 0.4 +
                scores['cost'] * 0.2 +
                scores['determinism'] * 0.1
            )
            
            scored_ideas.append({
                'idea': idea.to_dict(),
                'scores': scores,
                'total_score': total_score,
                'rationale': JudgeEngine._generate_rationale(idea, scores)
            })
        
        # Sort by total score (descending)
        scored_ideas.sort(key=lambda x: x['total_score'], reverse=True)
        
        return scored_ideas
    
    @staticmethod
    def _score_idea(idea: Idea, issue: str, system_info: Dict) -> Dict:
        """Score an idea across multiple criteria (0.0 - 1.0)."""
        scores = {}
        
        # Safety score (higher = safer)
        risk_map = {'low': 0.9, 'medium': 0.6, 'high': 0.2}
        scores['safety'] = risk_map.get(idea.risk, 0.5)
        
        # Success likelihood (higher = more likely to work)
        likelihood = 0.5  # Default
        
        # Boost score for OS-appropriate suggestions
        if 'ubuntu' in system_info.get('distro', '').lower():
            if any('nmcli' in check.lower() for check in idea.checks):
                likelihood += 0.3
            if any('systemctl' in check.lower() for check in idea.checks):
                likelihood += 0.2
        
        # Boost for category match
        issue_lower = issue.lower()
        if (idea.category == 'wifi' and any(w in issue_lower for w in ['wifi', 'wireless'])) or \
           (idea.category == 'dns' and any(w in issue_lower for w in ['dns', 'resolution'])) or \
           (idea.category == 'network' and any(w in issue_lower for w in ['network', 'interface'])):
            likelihood += 0.2
            
        scores['success_likelihood'] = min(likelihood, 1.0)
        
        # Cost score (higher = cheaper/faster)
        cost = 0.8  # Default: most commands are cheap
        if any('reboot' in fix.lower() for fix in idea.fixes):
            cost = 0.3  # Reboots are expensive
        if any('reinstall' in fix.lower() for fix in idea.fixes):
            cost = 0.1  # Reinstalls are very expensive
            
        scores['cost'] = cost
        
        # Determinism score (higher = more predictable)  
        determinism = 0.7  # Default
        if len(idea.checks) > 0:
            determinism += 0.2  # Has diagnostic steps
        if len(idea.fixes) > 1:
            determinism -= 0.1  # Multiple fixes = less predictable
            
        scores['determinism'] = min(determinism, 1.0)
        
        return scores
    
    @staticmethod
    def _generate_rationale(idea: Idea, scores: Dict) -> str:
        """Generate human-readable rationale for the scoring."""
        rationale = f"Scored {scores.get('total_score', 0):.2f}/1.0. "
        
        if scores['safety'] < 0.5:
            rationale += "⚠️  High risk approach. "
        elif scores['safety'] > 0.8:
            rationale += "✅ Safe approach. "
            
        if scores['success_likelihood'] > 0.7:
            rationale += "Strong success indicators. "
        elif scores['success_likelihood'] < 0.4:
            rationale += "Low success probability. "
            
        if scores['cost'] < 0.5:
            rationale += "High cost/time investment."
        
        return rationale.strip()