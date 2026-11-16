# Class 11 Mathematics — Study Notes: Sets, Relations and Functions

These are original revision notes written for testing Tailored Tuition. They follow the CBSE Class 11 syllabus order but are not textbook text.

## 1.1 Sets and their Representations

A set is a well-defined collection of objects. "Well-defined" means that for any object we can decide without doubt whether it belongs to the collection. "The vowels of the English alphabet" is a set; "the tall students in a class" is not, because "tall" is a matter of opinion.

The objects in a set are called its elements. We write $a \in A$ when $a$ is an element of $A$ and $b \notin A$ when it is not.

There are two common ways to describe a set:

- Roster form lists the elements inside braces, e.g. $A = \{1, 2, 3, 4\}$. Order does not matter and repeated elements are written once.
- Set-builder form describes a property shared by every element, e.g. $A = \{x : x \text{ is a natural number and } x < 5\}$.

## 1.2 Types of Sets

The empty set, written $\phi$ or $\{\}$, has no elements; for example $\{x : x \in \mathbb{N},\ 1 < x < 2\}$.
A finite set has a countable, limited number of elements; otherwise it is infinite. The number of elements of a finite set $A$ is written $n(A)$.
Two sets are equal when they have exactly the same elements.

## 1.3 Subsets and Power Sets

$A$ is a subset of $B$, written $A \subseteq B$, if every element of $A$ is also an element of $B$. Every set is a subset of itself and the empty set is a subset of every set.
The power set $P(A)$ is the set of all subsets of $A$. If $n(A) = m$ then $n(P(A)) = 2^m$. For example, $A = \{1, 2\}$ has subsets $\phi, \{1\}, \{2\}, \{1, 2\}$, so $n(P(A)) = 4$.
The universal set $U$ contains all the elements under consideration in a given context.

## 1.4 Operations on Sets

The union $A \cup B$ contains the elements that are in $A$, in $B$, or in both.
The intersection $A \cap B$ contains the elements that are in both $A$ and $B$. If $A \cap B = \phi$ the sets are disjoint.
The difference $A - B$ contains the elements of $A$ that are not in $B$.
The complement $A'$ contains the elements of the universal set that are not in $A$, so $A' = U - A$.

De Morgan's laws: $(A \cup B)' = A' \cap B'$ and $(A \cap B)' = A' \cup B'$.

Worked example: let $U = \{1, 2, 3, 4, 5, 6\}$, $A = \{1, 2, 3\}$, $B = \{2, 4\}$. Then $A \cup B = \{1, 2, 3, 4\}$, $A \cap B = \{2\}$, $A - B = \{1, 3\}$ and $A' = \{4, 5, 6\}$.

## 1.5 Venn Diagrams and Counting

A Venn diagram draws the universal set as a rectangle and sets as circles inside it, which makes overlaps easy to see.
For finite sets, $n(A \cup B) = n(A) + n(B) - n(A \cap B)$. We subtract the intersection because its elements were counted twice.

Worked example: in a class of 40 students, 25 play cricket, 18 play football and 8 play both. The number who play at least one game is $25 + 18 - 8 = 35$, so 5 students play neither.

## 2.1 Cartesian Product of Sets

An ordered pair $(a, b)$ has a first and a second element, so $(1, 2) \neq (2, 1)$.
The Cartesian product $A \times B$ is the set of all ordered pairs $(a, b)$ with $a \in A$ and $b \in B$. If $n(A) = p$ and $n(B) = q$ then $n(A \times B) = pq$.

## 2.2 Relations

A relation $R$ from $A$ to $B$ is any subset of $A \times B$. The set of first elements of the pairs in $R$ is its domain, the set of second elements is its range, and $B$ is the codomain.
Since $A \times B$ has $pq$ elements, there are $2^{pq}$ possible relations from $A$ to $B$.

## 2.3 Functions

A function $f$ from $A$ to $B$ is a relation in which every element of $A$ has exactly one image in $B$. We write $f : A \to B$ and $y = f(x)$.
Useful real functions include the identity function $f(x) = x$, constant functions, polynomial functions, the modulus function $f(x) = |x|$, the signum function and the greatest integer function $f(x) = [x]$.
To test whether a relation is a function, check that no element of the domain is paired with two different elements.
