import os
from typing import Dict, Any, List
from openai import OpenAI
from sqlalchemy.orm import Session
from .models import NewsArticle, Signal, BotLog


SYSTEM_PROMPT = (
    "You are a crypto trading assistant. Given a batch of recent news items, "
    "decide one action per target symbol: BUY, SELL or HOLD. Be conservative unless "
    "multiple articles support the same direction. Include confidence 0-100 and a brief reasoning. "
    "\n\nIMPORTANT: Also provide broader market context. If news mentions a specific sector (e.g., mining, DeFi, gaming), "
    "also recommend related coins in that sector even if they weren't directly mentioned in the news. "
    "Look for themes and patterns across articles to identify emerging trends."
)


class AIDecider:
    def __init__(self, model: str = None):
        api_key = os.getenv('OPENAI_API_KEY')
        self.client = OpenAI(api_key=api_key) if api_key else None
        self.model = model or os.getenv('OPENAI_MODEL', 'gpt-4o-mini')

    def decide(self, db: Session, symbols: List[str], lookback_minutes: int = 60) -> List[Signal]:
        # fetch latest articles for symbols by ticker field containment
        # naive: filter by substring in tickers column
        articles = db.query(NewsArticle).order_by(NewsArticle.date.desc()).limit(200).all()
        
        log_msg = f"AI Decider: Found {len(articles)} total articles, analyzing {len(symbols)} symbols"
        print(f"[AI Decider] {log_msg}")
        try:
            db.add(BotLog(level='INFO', category='AI', message=log_msg))
            db.commit()
        except:
            pass
        
        relevant = [a for a in articles if any(s.replace('USDT','') in (a.tickers or '') for s in symbols)]
        
        log_msg2 = f"AI Decider: Found {len(relevant)} relevant articles for these symbols"
        print(f"[AI Decider] {log_msg2}")
        try:
            db.add(BotLog(level='INFO', category='AI', message=log_msg2))
            db.commit()
        except:
            pass
        
        if not relevant:
            log_msg3 = f"AI Decider: No relevant articles found - cannot generate signals"
            print(f"[AI Decider] {log_msg3}")
            try:
                db.add(BotLog(level='WARNING', category='AI', message=log_msg3))
                db.commit()
            except:
                pass
            return []

        items = [
            {
                'title': a.title,
                'sentiment': a.sentiment,
                'source': a.source_name,
                'date': a.date.isoformat() if a.date else None,
                'tickers': a.tickers,
                'url': a.news_url,
                'summary': (a.text or '')[:500]
            }
            for a in relevant[:30]
        ]

        decisions = []
        if self.client is not None:
            try:
                user_msg = {
                    'role': 'user',
                    'content': (
                        "Analyze the following news for ALL mentioned symbols: " + ", ".join(symbols) + "\n\n" +
                        "News JSON: " + str(items) + "\n\n" +
                        "Instructions:\n" +
                        "1. For each symbol with direct news, provide: {symbol, action, confidence, reasoning, ref_url}\n" +
                        "2. Identify themes/sectors mentioned (e.g., mining, DeFi, gaming, NFTs, Layer-2)\n" +
                        "3. For important themes, recommend related coins even if not directly mentioned\n" +
                        "4. Return a JSON list of ALL recommendations (both direct and related)\n" +
                        "5. Be specific about WHY related coins are recommended (e.g., 'Mining sector bullish due to BTC news')"
                    )
                }

                chat = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{'role': 'system', 'content': SYSTEM_PROMPT}, user_msg],
                    temperature=0.2
                )
                content = chat.choices[0].message.content

                try:
                    import json
                    decisions = json.loads(content)
                    print(f"[AI Decider] OpenAI returned {len(decisions)} decisions")
                except Exception as e:
                    print(f"[AI Decider] Failed to parse OpenAI response: {e}")
                    print(f"[AI Decider] Raw content: {content[:500]}")
                    decisions = []
            except Exception as e:
                print(f"[AI Decider] OpenAI API call failed: {e}")
                decisions = []
        else:
            # Fallback heuristic without OpenAI: majority sentiment per symbol
            from collections import defaultdict
            sym_counts = defaultdict(lambda: {'pos': 0, 'neg': 0, 'ref': None})
            for a in relevant:
                syms = [s.strip().upper() for s in (a.tickers or '').split(',') if s.strip()]
                for s in symbols:
                    base = s.replace('USDT', '')
                    if base in syms:
                        if (a.sentiment or '').lower().startswith('pos'):
                            sym_counts[s]['pos'] += 1
                        elif (a.sentiment or '').lower().startswith('neg'):
                            sym_counts[s]['neg'] += 1
                        if not sym_counts[s]['ref']:
                            sym_counts[s]['ref'] = a.news_url
            for s in symbols:
                c = sym_counts[s]
                action = 'HOLD'
                confidence = 50
                reasoning = 'Mixed or insufficient sentiment (fallback)'
                
                # LOWERED THRESHOLDS - generate signals with ANY news
                if c['pos'] >= 1 and c['neg'] == 0:
                    action = 'BUY'
                    confidence = 65
                    reasoning = f"Positive news ({c['pos']} articles) with no negatives (fallback)"
                elif c['neg'] >= 1 and c['pos'] == 0:
                    action = 'SELL'
                    confidence = 65
                    reasoning = f"Negative news ({c['neg']} articles) with no positives (fallback)"
                elif c['pos'] > c['neg'] and c['pos'] >= 1:
                    action = 'BUY'
                    confidence = 55
                    reasoning = f"More positive ({c['pos']}) than negative ({c['neg']}) news (fallback)"
                elif c['neg'] > c['pos'] and c['neg'] >= 1:
                    action = 'SELL'
                    confidence = 55
                    reasoning = f"More negative ({c['neg']}) than positive ({c['pos']}) news (fallback)"
                elif c['pos'] > 0 or c['neg'] > 0:
                    # Generate HOLD signal if there's ANY news
                    reasoning = f"News sentiment: {c['pos']} positive, {c['neg']} negative (fallback HOLD)"
                    confidence = 50
                
                print(f"[AI Decider] Fallback decision for {s}: {action} ({confidence}%) - {reasoning}")
                decisions.append({
                    'symbol': s,
                    'action': action,
                    'confidence': confidence,
                    'reasoning': reasoning,
                    'ref_url': c['ref']
                })

        signals: List[Signal] = []
        print(f"[AI Decider] Processing {len(decisions)} decisions")
        
        log_msg_decisions = f"AI Decider: Processing {len(decisions)} decisions from OpenAI/fallback"
        try:
            db.add(BotLog(level='INFO', category='AI', message=log_msg_decisions))
            db.commit()
        except:
            pass
        
        for d in decisions:
            sig = Signal(
                symbol=d.get('symbol'),
                action=d.get('action', 'HOLD'),
                confidence=int(d.get('confidence', 0)),
                reasoning=d.get('reasoning', ''),
                ref_article_url=d.get('ref_url'),
                meta=d
            )
            db.add(sig)
            signals.append(sig)
            print(f"[AI Decider] Created signal: {sig.symbol} {sig.action} ({sig.confidence}%)")
        
        if signals:
            db.commit()
            log_msg_success = f"AI Decider: Created {len(signals)} signals - {', '.join([f'{s.symbol} {s.action}' for s in signals[:5]])}{'...' if len(signals) > 5 else ''}"
            print(f"[AI Decider] {log_msg_success}")
            try:
                db.add(BotLog(level='INFO', category='AI', message=log_msg_success))
                db.commit()
            except:
                pass
        else:
            log_msg_none = f"AI Decider: No signals generated from {len(decisions)} decisions"
            print(f"[AI Decider] {log_msg_none}")
            try:
                db.add(BotLog(level='WARNING', category='AI', message=log_msg_none))
                db.commit()
            except:
                pass
        
        return signals


