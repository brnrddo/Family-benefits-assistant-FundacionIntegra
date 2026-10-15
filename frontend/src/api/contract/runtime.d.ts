export declare function ucs2length(str: string): number;
export declare function equal(a: unknown, b: unknown): boolean;
export declare const formats: Readonly<{
  uuid: (value: string) => boolean;
  date: (value: string) => boolean;
  'date-time': (value: string) => boolean;
  uri: (value: string) => boolean;
}>;
