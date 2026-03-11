// @ts-expect-error Babel standalone does not ship useful TS types for this setup.
import * as Babel from "@babel/standalone";

type BabelResult = {
  code?: string;
};

const MODULE_PLUGIN = "transform-modules-commonjs";

export async function compileJSX(sourceCode: string): Promise<string> {
  try {
    const result = Babel.transform(sourceCode, {
      presets: [["react", { runtime: "classic" }]],
      plugins: [MODULE_PLUGIN]
    }) as BabelResult;

    if (!result.code) {
      throw new Error("Babel returned an empty program");
    }

    return result.code;
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    throw new Error(`Compilation error: ${message}`);
  }
}
