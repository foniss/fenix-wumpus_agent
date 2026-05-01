import random

class LogicEngine:
    def __init__(self):
        self.kb = set()
        self.inference_steps = 0

    def tell(self, clause):
        # Adds a rule to the Knowledge Base
        self.kb.add(frozenset(clause))

    def ask(self, query_clause):
        """
        Proof by Contradiction: To prove the query is True, 
        we add the OPPOSITE of the query to the KB and run DPLL.
        If DPLL finds it 'unsatisfiable', our original query MUST be True.
        """
        negated_query = (query_clause[0], not query_clause[1])
        test_clauses = list(self.kb) + [frozenset([negated_query])]
        
        self.inference_steps = 0
        
        # If unsatisfiable (False), then the query is entailed (True)
        return not self._dpll(test_clauses)

    def _dpll(self, clauses):
        """
        Davis-Putnam-Logemann-Loveland (DPLL) Algorithm
        This is an industry-standard, high-speed SAT solver.
        """
        self.inference_steps += 1
        
        # Safety net: prevent absolute infinite loops on massive grids
        if self.inference_steps > 3000:
            return True 
            
        # 1. Base Case: If there are no clauses left, the logic is satisfied
        if not clauses:
            return True
            
        # 2. Base Case: If an empty clause exists, it is an impossible contradiction
        if any(len(c) == 0 for c in clauses):
            return False
            
        # 3. UNIT PROPAGATION (The secret to speed)
        # If we know a fact for absolute certain (e.g., "P_1_1 is False"),
        # propagate it immediately to simplify all other rules.
        unit_clauses = [c for c in clauses if len(c) == 1]
        if unit_clauses:
            unit_literal = list(unit_clauses[0])[0]
            return self._dpll(self._propagate(clauses, unit_literal))
            
        # 4. BRANCHING
        # If no units are left, guess a truth value and branch.
        first_clause = clauses[0]
        sym = list(first_clause)[0][0] # Get the string name, e.g., "P_1_1"
        
        # Guess True
        if self._dpll(self._propagate(clauses, (sym, True))):
            return True
            
        # Guess False
        return self._dpll(self._propagate(clauses, (sym, False)))
        
    def _propagate(self, clauses, literal):
        """
        Simplifies the Knowledge Base using a known literal.
        """
        new_clauses = []
        neg_literal = (literal[0], not literal[1])
        for clause in clauses:
            if literal in clause:
                # If the clause contains our known True literal, the whole clause is True. Discard it.
                continue 
            if neg_literal in clause:
                # If the clause contains the known False literal, remove that literal from the clause.
                new_clauses.append(frozenset(l for l in clause if l != neg_literal))
            else:
                new_clauses.append(clause)
        return new_clauses


class Grid:
    def __init__(self, rows=4, cols=4, pit_prob=0.15):
        self.rows = rows
        self.cols = cols
        self.pits = set()
        self.wumpus = None
        self._generate_hazards(pit_prob)

    def _generate_hazards(self, pit_prob):
        cells = [(r, c) for r in range(self.rows) for c in range(self.cols)]
        valid_hazards = [c for c in cells if c != (0, 0)] 
        
        self.wumpus = random.choice(valid_hazards)
        for cell in valid_hazards:
            if cell != self.wumpus and random.random() < pit_prob:
                self.pits.add(cell)

    def get_percepts(self, r, c):
        breeze = False
        stench = False
        for ar, ac in self.get_adjacent(r, c):
            if (ar, ac) in self.pits: breeze = True
            if (ar, ac) == self.wumpus: stench = True
        return {"breeze": breeze, "stench": stench}

    def get_adjacent(self, r, c):
        adj = []
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = r + dr, c + dc
            if 0 <= nr < self.rows and 0 <= nc < self.cols:
                adj.append((nr, nc))
        return adj


class Agent:
    def __init__(self, grid):
        self.grid = grid
        self.logic = LogicEngine()
        self.pos = (0, 0)
        self.visited = set()
        self.known_safe = set()
        self.known_hazards = set()
        self.is_dead = False
        
        # Start space is always safe
        self.logic.tell([("P_0_0", False)])
        self.logic.tell([("W_0_0", False)])
        self._perceive_and_update()

    def move(self, direction):
        if self.is_dead: return False

        r, c = self.pos
        if direction == "up" and r > 0: r -= 1
        elif direction == "down" and r < self.grid.rows - 1: r += 1
        elif direction == "left" and c > 0: c -= 1
        elif direction == "right" and c < self.grid.cols - 1: c += 1
        else: return False
            
        self.pos = (r, c)
        
        if self.pos in self.grid.pits or self.pos == self.grid.wumpus:
            self.is_dead = True
            self.known_hazards.add(self.pos)
            return True

        if self.pos not in self.visited:
            self.logic.tell([(f"P_{r}_{c}", False)])
            self.logic.tell([(f"W_{r}_{c}", False)])
            self._perceive_and_update()
            
        return True

    def _perceive_and_update(self):
        r, c = self.pos
        self.visited.add((r, c))
        self.known_safe.add((r, c))
        
        percepts = self.grid.get_percepts(r, c)
        adj = self.grid.get_adjacent(r, c)
        
        # Tell the KB about Pits based on Breeze
        b_sym = f"B_{r}_{c}"
        self.logic.tell([(b_sym, percepts["breeze"])])
        pit_literals = [(f"P_{ar}_{ac}", True) for ar, ac in adj]
        self.logic.tell([(b_sym, False)] + pit_literals)
        for p_lit in pit_literals:
            self.logic.tell([(p_lit[0], False), (b_sym, True)])

        # Tell the KB about Wumpus based on Stench
        s_sym = f"S_{r}_{c}"
        self.logic.tell([(s_sym, percepts["stench"])])
        wumpus_literals = [(f"W_{ar}_{ac}", True) for ar, ac in adj]
        self.logic.tell([(s_sym, False)] + wumpus_literals)
        for w_lit in wumpus_literals:
            self.logic.tell([(w_lit[0], False), (s_sym, True)])

        # Evaluate the entire global frontier to ensure all known hazards render
        self._evaluate_global_frontier()

    def _evaluate_global_frontier(self):
        # 1. Gather every single unknown cell that borders ANY visited cell
        frontier = set()
        for vr, vc in self.visited:
            for ar, ac in self.grid.get_adjacent(vr, vc):
                if (ar, ac) not in self.visited and \
                   (ar, ac) not in self.known_safe and \
                   (ar, ac) not in self.known_hazards:
                    frontier.add((ar, ac))
                    
        # 2. Ask the Knowledge Base about all of them
        for ar, ac in frontier:
            is_pit = self.logic.ask((f"P_{ar}_{ac}", True))
            is_wumpus = self.logic.ask((f"W_{ar}_{ac}", True))
            is_not_pit = self.logic.ask((f"P_{ar}_{ac}", False))
            is_not_wumpus = self.logic.ask((f"W_{ar}_{ac}", False))
            
            if is_not_pit and is_not_wumpus:
                self.known_safe.add((ar, ac))
            elif is_pit or is_wumpus:
                self.known_hazards.add((ar, ac))

    def get_state(self):
        r, c = self.pos
        return {
            "grid_size": {"rows": self.grid.rows, "cols": self.grid.cols},
            "agent_pos": {"r": r, "c": c},
            "percepts": self.grid.get_percepts(r, c),
            "visited": list(self.visited),
            "known_safe": list(self.known_safe),
            "known_hazards": list(self.known_hazards),
            "inference_steps": self.logic.inference_steps,
            "is_dead": self.is_dead,
            "actual_pits": list(self.grid.pits),
            "actual_wumpus": self.grid.wumpus
        }