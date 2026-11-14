# Demo walkthrough

About 5 minutes. Start the system first, as in the README. Works with no AI key.

**The shortest path, about 90 seconds**

1. Open http://127.0.0.1:5173, press **Try as a learner**, then **Start learning**.
2. Go to `http://127.0.0.1:5173/problems/sum-to-n`, and replace the code with:

   ```python
   def sum_to_n(n):
       total = 0
       x = = 1
       return total
   ```
3. Press **Ask for a hint** six times. Each press gives a different kind of help, and the sixth says it will wait for a code change.
4. Open **Why this hint?** on any of them to see the evidence behind it.
   Then open **Learn** beside the problem, and switch between Guided, Practice, Revision and Interview prep to see what changes.
   Then select a line in the code, type what confuses you in the box under the tutor, and press Enter. The question is answered even though every hint has been shown.
5. Replace the code with one that has a loop ending one step early, using `range(1, n)`, and ask again. The tutor acknowledges that the syntax error is fixed, and starts small on the new issue.
6. Go to **Add question**, then **Import from a link**, and enter a LeetCode link to see why it asks you to paste.

The full walkthrough follows.

**Learner**

1. Open http://127.0.0.1:5173 and press **Try as a learner**. Note the label saying it is not a secure account.
2. Choose "I'm brand new", then **Start learning**. Home recommends **Say Hello**, and says why.
3. Press **Start**. Point out the short walkthrough, the examples and the three separate actions.
4. Press **Run** with the starter code. It is not graded, and the example shows expected and actual values.
5. Replace the code with `def greet(name): return "Hello " + name`, and watch the "earlier version" label appear on the old results.
6. Press **Submit**. Show the order: what happened, next action, tests. In the Tutor panel, open **Why this hint?**
7. Press **Submit** again after adding a comment, to show the same issue moving to the next kind of help, with the reason.
8. Press **I need more help**, then show that nothing else happens until you act.
9. Fix it with `def greet(name): return f"Hello, {name}!"` and **Submit**. Show the reflection question and the next step. It suggests similar practice, not advancing after one success.
10. Open **Progress**. Show ranges rather than exact scores, the "What does this estimate mean?" explanation, and that measured improvement is unavailable without both checks.

**Add a question**

11. Go to **Practice**, then **Add question**, then **Paste question**. Paste:

    ```text
    Two Sum
    Easy
    Given an array of integers nums and an integer target, return indices of the two numbers that add up to target.

    Example 1:
    Input: nums = [2,7,11,15], target = 9
    Output: [0,1]

    Constraints:
    2 <= nums.length <= 500
    ```
12. Review the extracted details. On the tests step, show the "not the original platform's hidden tests" note and the generated tests that stay off until given an answer. Save, then submit a wrong answer to show the same tutor at work.
13. Try **Import from a link** with a LeetCode URL for the explanation, with `1872A` for Codeforces metadata, and with `https://projecteuler.net/problem=1` to see a page actually read, with what was found and what is missing. Those last two need internet access.
13a. Back on **Add a question**, show that the import options come first and **Previously added questions** sits below them, closed, with a count. Open it with the keyboard (Tab, then Enter).
13b. On any problem, open **Test cases** → **Hidden** to show how many hidden tests there are and what kinds of case they cover, without their inputs. Each generated test on an imported question also says what it checks.

**Teacher**

14. Sign out, then **Try as a teacher**. Show the synthetic-data warning, the formulas, the learners flagged with evidence and uncertainty, and common errors.

**Engineering**

15. Show failure handling by stopping the execution service and pressing **Run**. The app says it is a problem on its side, and your code stays. Restart it and try again.
16. Open `http://127.0.0.1:8101/api/docs` for the API, and `backend/app/tutoring/policy.yaml` to show DSDA's settings.
17. Run the agent audit against the running stack, and open the report it writes. Each row shows what every agent produced, including the exact hint, and the checks below each scenario pass or fail:

    ```bash
    backend/.venv/bin/python scripts/agent_audit.py http://127.0.0.1:8101 > docs/agent-audit-run.md
    ```
